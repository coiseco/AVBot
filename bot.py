import telebot
import json
import os
import time
from telebot.types import ReplyKeyboardRemove, MenuButtonCommands

# Токен и ID админа
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [5565292941]

bot = telebot.TeleBot(TOKEN)

# Файлы
SUBSCRIBERS_FILE = 'subscribers.json'
CONFIG_FILE = 'config.json'
SOUND_FILE = 'sound_settings.json'

# Загрузка данных
def load_json(file, default):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

subscribers = set(load_json(SUBSCRIBERS_FILE, []))
config = load_json(CONFIG_FILE, {'welcome_message': 'Привет! Это новостной бот канала. С ним ты не пропустишь все важные события.'})
sound_settings = load_json(SOUND_FILE, {})

# Сохранение
def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_subscribers(): save_json(SUBSCRIBERS_FILE, list(subscribers))
def save_config(): save_json(CONFIG_FILE, config)
def save_sound_settings(): save_json(SOUND_FILE, sound_settings)

# /start — только приветствие и включение меню
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Добавляем в подписчики
    if user_id not in subscribers:
        subscribers.add(user_id)
        save_subscribers()

    # Отправляем только приветствие
    bot.send_message(chat_id, config['welcome_message'], parse_mode="HTML")

    # Для админа ничего больше не делаем
    if user_id in ADMIN_IDS:
        return

    # Включаем кнопку "Меню" с командами
    bot.set_chat_menu_button(
        chat_id=chat_id,
        menu_button=MenuButtonCommands(type="commands")
    )

# Обработка команд из меню: /admin, /sound, /unsubscribe
@bot.message_handler(commands=['admin', 'sound', 'unsubscribe'])
def menu_commands(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    command = message.text.split()[0][1:]  # чистая команда без /

    if user_id in ADMIN_IDS:
        return

    # Удаляем сообщение с командой (чтобы чат остался чистым)
    try:
        bot.delete_message(chat_id, message.message_id)
    except:
        pass

    if command == 'admin':
        bot.send_message(
            chat_id,
            "👤 Нажмите ниже, чтобы написать записаться на тестирование:",
            reply_markup=telebot.types.InlineKeyboardMarkup().add(
                telebot.types.InlineKeyboardButton("Записаться", url=f"tg://user?id={ADMIN_IDS[0]}")
            )
        )

    elif command == 'sound':
        current = sound_settings.get(user_id, True)
        sound_settings[user_id] = not current
        save_sound_settings()

        status = "включён 🔔" if not current else "выключен 🔕"
        bot.send_message(chat_id, f"🔊 Звук уведомлений теперь <b>{status}</b>", parse_mode="HTML")

    elif command == 'unsubscribe':
        if user_id in subscribers:
            subscribers.remove(user_id)
            save_subscribers()
            sound_settings.pop(user_id, None)
            save_sound_settings()

        bot.send_message(
            chat_id,
            "🚫 Вы успешно отписались от уведомлений.\n\nЧтобы вернуться — нажмите /start снова."
        )

# Рассылка от админа (любое текстовое сообщение без /)
@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text and not m.text.startswith('/'))
def admin_broadcast(message):
    failed = 0
    total = len(subscribers)
    
    for user_id in list(subscribers):
        try:
            silent = not sound_settings.get(user_id, True)  # без звука, если выключен
            bot.send_message(user_id, message.text, disable_notification=silent)
        except Exception:
            subscribers.discard(user_id)
            sound_settings.pop(user_id, None)
            failed += 1
    
    save_subscribers()
    save_sound_settings()
    bot.reply_to(message, f'Рассылка завершена.\nДоставлено: {total - failed}\nНе удалось: {failed}')

# /setwelcome — только для админа
@bot.message_handler(commands=['setwelcome'])
def set_welcome(message):
    if message.from_user.id in ADMIN_IDS:
        new_text = message.text.replace('/setwelcome', '').strip()
        if new_text:
            config['welcome_message'] = new_text
            save_config()
            bot.reply_to(message, "Приветствие успешно обновлено!")
        else:
            bot.reply_to(message, "Укажите текст после команды, например:\n/setwelcome Новый текст приветствия")
    else:
        bot.send_message(message.chat.id, "Эта команда доступна только администратору.")

# Игнорируем (и по желанию удаляем) любые другие сообщения от пользователей
@bot.message_handler(func=lambda m: m.from_user.id not in ADMIN_IDS)
def ignore_messages(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass  # если не удалось удалить — ничего страшного

print("Бот запущен...")

# Защищённый polling
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"[CRITICAL] Polling упал: {e}")
        time.sleep(5)