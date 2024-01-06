import telebot
import gspread
import sqlite3
from oauth2client.service_account import ServiceAccountCredentials
from telebot import types
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# Инициализация бота
bot = telebot.TeleBot('6332665358:AAHXpmnyWO4yKza0GAvgcy6nCFVwETs1aaA')

# Подключение к Google Sheets
scope = 'https://spreadsheets.google.com/feeds https://www.googleapis.com/auth/drive'
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    r'C:\Users\Пользователь\PycharmProjects\sch1584bot\sch1584-0b47bcc851fb.json', scope)
gc = gspread.authorize(credentials)

# ID вашей таблицы
spreadsheet_id = '1dA-RLiyEI3MtV5uFNvEIGG913b_HtAy18gGxkXt1JWI'

# Откройте таблицу
worksheet = gc.open_by_key(spreadsheet_id).sheet1  # Предполагается, что данные в первом листе

# Имя файла базы данных SQLite
DB_FILE = 'user_states.db'

def create_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            selected_classes TEXT,
            expected_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user_classes(user_id, selected_classes):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_states (user_id, selected_classes) VALUES (?, ?)
    ''', (user_id, selected_classes))
    conn.commit()
    conn.close()

def save_expected_time(user_id, expected_time):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE user_states SET expected_time = ? WHERE user_id = ?
    ''', (expected_time, user_id))
    conn.commit()
    conn.close()

def load_user_classes(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT selected_classes FROM user_states WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0].split(",") if result else None

def load_expected_time(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT expected_time FROM user_states WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Декоратор для команды "/start"
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    create_tables()

    # Приветственное сообщение
    welcome_message = (
        "Это бот школы 1584 для классных руководителей. "
        "Он предназначен для оповещения об отсутствующих учениках. "
        "Для начала использования, вам необходимо пройти регистрацию.\n\n"
        "Доступные команды:\n"
        "/choose_class - выбрать класс\n"
        "/mark_absence - отметить отсутствующих"
    )

    # Упоминание создателя бота и контактной информации
    contact_info = "По всем вопросам можно обращаться к @ascher_work."

    bot.send_message(user_id, welcome_message)
    bot.send_message(user_id, contact_info)

# Логика обработки выбора класса для отметки отсутствующих
def choose_class_for_absence(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Получаем список классов пользователя
    user_classes = load_user_classes(user_id)

    # Создаем кнопки для выбора класса
    class_buttons = [
        types.InlineKeyboardButton(class_name, callback_data=f"absence_{class_name}") for class_name in user_classes
    ]

    # Разбиваем кнопки по две в каждом столбце
    class_keyboard = types.InlineKeyboardMarkup(row_width=2)
    class_keyboard.add(*class_buttons)

    # Отправляем сообщение с Inline-клавиатурой для выбора класса
    bot.send_message(chat_id, "Выберите класс для отметки отсутствующих:", reply_markup=class_keyboard)

# Декоратор для обработки выбора класса для отметки отсутствующих
@bot.callback_query_handler(func=lambda call: call.data.startswith('absence_'))
def handle_class_selection_for_absence(call):
    user_id = call.from_user.id
    selected_class = call.data.split('_')[1]

    # Обрабатываем выбор класса для отметки отсутствующих
    handle_mark_absence_single_class(call.message.chat.id, user_id, selected_class)

# Логика обработки отметки отсутствующих для одного класса
def handle_mark_absence_single_class(chat_id, user_id, selected_class):
    # Получаем список учеников для выбранного класса
    students_for_class = get_students_for_class(selected_class)

    # Создаем кнопки для выбора статуса отсутствия
    absence_buttons = [
        types.InlineKeyboardButton("Отсутствует по болезни", callback_data=f"reason_illness_{selected_class}"),
        types.InlineKeyboardButton("Отсутствует по семейным обстоятельствам", callback_data=f"reason_family_{selected_class}"),
        types.InlineKeyboardButton("Придет к ... уроку", callback_data=f"reason_coming_{selected_class}")
    ]

    # Разбиваем кнопки по две в каждом столбце
    absence_keyboard = types.InlineKeyboardMarkup(row_width=2)
    absence_keyboard.add(*absence_buttons)

    # Отправляем сообщение с Inline-клавиатурой для выбора статуса отсутствия
    bot.send_message(chat_id, f"Выберите статус отсутствия для учеников в классе {selected_class}:", reply_markup=absence_keyboard)

# Декоратор для обработки выбора статуса отсутствия
@bot.callback_query_handler(func=lambda call: call.data.startswith('reason_'))
def handle_absence_reason_selection(call):
    user_id = call.from_user.id
    data_parts = call.data.split('_')
    reason = data_parts[1]
    selected_class = data_parts[2]

    # Обрабатываем выбор статуса отсутствия
    if reason == 'coming':
        # Если выбрана опция "Придет к ... уроку", предоставляем список уроков
        choose_lesson_for_coming_reason(call.message.chat.id, user_id, selected_class)
    else:
        # В противном случае, отправляем сообщение о выборе статуса отсутствия
        bot.send_message(call.message.chat.id, f"Выбран статус отсутствия '{reason}' для класса {selected_class}")

# Логика обработки выбора урока при статусе "Придет к ... уроку"
def choose_lesson_for_coming_reason(chat_id, user_id, selected_class):
    # Создаем кнопки для выбора урока
    lesson_buttons = [
        types.InlineKeyboardButton(str(i), callback_data=f"lesson_{i}_{selected_class}") for i in range(2, 7)
    ]

    # Разбиваем кнопки по две в каждом столбце
    lesson_keyboard = types.InlineKeyboardMarkup(row_width=2)
    lesson_keyboard.add(*lesson_buttons)

    # Отправляем сообщение с Inline-клавиатурой для выбора урока
    bot.send_message(chat_id, f"Выберите урок, когда ученик придет в класс {selected_class}:", reply_markup=lesson_keyboard)

# Декоратор для обработки выбора урока при статусе "Придет к ... уроку"
@bot.callback_query_handler(func=lambda call: call.data.startswith('lesson_'))
def handle_lesson_selection_for_coming_reason(call):
    data_parts = call.data.split('_')
    lesson_number = data_parts[1]
    selected_class = data_parts[2]

    # Обрабатываем выбор урока при статусе "Придет к ... уроку"
    bot.send_message(call.message.chat.id, f"Выбран урок {lesson_number} для класса {selected_class}")

# Декоратор для команды /mark_absence
@bot.message_handler(commands=['mark_absence'])
def mark_absence(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Получаем список классов пользователя
    user_classes = load_user_classes(user_id)

    if not user_classes:
        # Если у пользователя нет выбранных классов, предлагаем ему выбрать класс
        choose_class(message)
    elif len(user_classes) == 1:
        # Если у пользователя есть только один класс, предоставляем ему список учеников для отметки
        handle_mark_absence_single_class(chat_id, user_id, user_classes[0])
    else:
        # Если у пользователя есть два класса, предоставляем ему выбор класса
        choose_class_for_absence(message)

# Остальной функционал...

if __name__ == "__main__":
    # Создаем таблицы в базе данных, если их нет
    create_tables()

    # Запуск бота
    bot.polling(none_stop=True)