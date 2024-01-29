import telebot
import gspread
import sqlite3
from oauth2client.service_account import ServiceAccountCredentials
from telebot import types
#from telegram import InlineKeyboardButton, InlineKeyboardMarkup
#from telegram.ext import CallbackQueryHandler

# Инициализация бота
bot = telebot.TeleBot('6332665358:AAHXpmnyWO4yKza0GAvgcy6nCFVwETs1aaA')

# Подключение к Google Sheets
scope = 'https://spreadsheets.google.com/feeds https://www.googleapis.com/auth/drive'
credentials = ServiceAccountCredentials.from_json_keyfile_name(r'C:\Users\Пользователь\PycharmProjects\sch1584bot\sch1584-0b47bcc851fb.json', scope)
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
            selected_parallel TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user_state(user_id, selected_parallel):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_states (user_id, selected_parallel) VALUES (?, ?)
    ''', (user_id, selected_parallel))
    conn.commit()
    conn.close()

def load_user_state(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT selected_parallel FROM user_states WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
# Декоратор для обработки команды /start
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id

    # Приветственный текст
    welcome_text = (
        "Привет! Это бот школы 1584 для классных руководителей. Он предназначен для оповещения об отсутствующих учениках. "
        "Для начала использования, вам необходимо пройти регистрацию.\n\n"
        "Доступные команды:\n"
        "/choose_class - выбрать свой класс и начать работу с ботом\n"
        "/help - получить список доступных команд\n\n"
        "По всем вопросам обращайтесь к @ascher_work"
    )

    # Отправляем приветственное сообщение
    bot.send_message(chat_id, welcome_text)


# Декоратор для обработки команды /help
@bot.message_handler(commands=['help'])
def help_command(message):
    chat_id = message.chat.id

    # Список доступных команд
    commands_text = (
        "Доступные команды:\n"
        "/choose_class - выбрать свой класс и начать работу с ботом\n"
        "/help - получить список доступных команд\n\n"
        "По всем вопросам обращайтесь к @ascher_work"
    )

    # Отправляем сообщение со списком команд
    bot.send_message(chat_id, commands_text)


# Декоратор для команды "choose_class"
@bot.message_handler(commands=['choose_class'])
def choose_class(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Загружаем состояние пользователя (выбранную параллель)
    selected_parallel = load_user_state(user_id)

    # Создаем кнопки для выбора параллели
    parallel_buttons = [
        types.InlineKeyboardButton(str(i), callback_data=f"parallel_{i}") for i in range(5, 12)
    ]

    # Разбиваем кнопки по две в каждом столбце
    parallel_keyboard = types.InlineKeyboardMarkup(row_width=2)
    parallel_keyboard.add(*parallel_buttons)
    # Если у пользователя уже есть выбранная параллель, отправляем сообщение об этом
    if selected_parallel:
        bot.send_message(chat_id, f"Ваша текущая параллель: {selected_parallel}")
    else:
    # Отправляем сообщение с Inline-клавиатурой для выбора параллели
        bot.send_message(chat_id, "Выберите свою параллель:", reply_markup=parallel_keyboard)


# Декоратор для обработки Inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('parallel_'))
def handle_parallel_selection(call):
    user_id = call.from_user.id
    selected_parallel = call.data.split('_')[1]

    # Обрабатываем выбор параллели
    bot.send_message(call.message.chat.id, f"Вы выбрали параллель: {selected_parallel}")

    # Сохраняем состояние пользователя (выбранную параллель)
    save_user_state(user_id, selected_parallel)

    # Получаем список уникальных классов из столбца "Класс" в Google Sheets
    class_column = worksheet.col_values(2)[1:]

    # Фильтруем классы по выбранной параллели и сортируем
    classes_for_parallel = sorted(
        set(class_name for class_name in class_column if class_name.startswith(selected_parallel)))

    # Создаем кнопки для выбора класса
    class_buttons = [
        types.InlineKeyboardButton(class_name, callback_data=f"class_{user_id}_{class_name}") for class_name in
        classes_for_parallel
    ]

    # Разбиваем кнопки по две в каждом столбце
    class_keyboard = types.InlineKeyboardMarkup(row_width=2)
    class_keyboard.add(*class_buttons)

    # Отправляем сообщение с Inline-клавиатурой для выбора класса
    bot.send_message(call.message.chat.id, "Выберите свой класс:", reply_markup=class_keyboard)


# Декоратор для обработки Inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('class_'))
def handle_class_selection(call):
    user_id, selected_class = call.data.split('_')[1:]

    # Обрабатываем выбор класса
    bot.send_message(call.message.chat.id, f"Вы выбрали класс: {selected_class}")

    # Сохраняем состояние пользователя (выбранный класс)
    save_user_state(user_id, selected_class)

    # Получаем список учеников для выбранного класса
    students_for_class = get_students_for_class(selected_class)

    # Отправляем список учеников учителю
    bot.send_message(call.message.chat.id,
                     f"Список учеников в классе {selected_class}:\n" + "\n".join(students_for_class))


# Декоратор для обработки текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    user_message = message.text.lower()

    # Логика обработки выбора класса
    class_column = worksheet.col_values(2)[1:]
    unique_classes = list(set(class_column))

    if user_message in unique_classes:
        handle_class_selection(chat_id, user_message)
    else:
        # Логика обработки других сообщений, если не выбран класс
        bot.send_message(chat_id, "Пожалуйста, выберите свой класс с помощью команды /choose_class")

# Логика обработки выбора класса
def handle_class_selection(chat_id, selected_class):
    # Получаем список учеников для выбранного класса
    students_for_class = get_students_for_class(selected_class)

    # Отправляем список учеников учителю
    bot.send_message(chat_id, f"Список учеников в классе {selected_class}:\n" + "\n".join(students_for_class))

def get_students_for_class(selected_class):
    class_column = worksheet.col_values(2)[1:]
    name_column = worksheet.col_values(1)[1:]

    # Получаем индексы учеников для выбранного класса
    indices = [i for i, class_name in enumerate(class_column) if class_name == selected_class]

    # Сортируем учеников по алфавиту на основе их индексов
    sorted_students = sorted([(name_column[i], i) for i in indices])

    # Возвращаем отсортированный список имен учеников
    return [student[0] for student in sorted_students]


if __name__ == "__main__":
    # Создаем таблицы в базе данных, если их нет
    create_tables()

    # Запуск бота
    bot.polling(none_stop=True)