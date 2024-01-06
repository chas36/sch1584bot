import telebot
import gspread
import sqlite3
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from telebot import types
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# Инициализация бота
bot = telebot.TeleBot('6332665358:AAHXpmnyWO4yKza0GAvgcy6nCFVwETs1aaA')

# Подключение к Google Sheets
scope = 'https://spreadsheets.google.com/feeds https://www.googleapis.com/auth/drive'
credentials = ServiceAccountCredentials.from_json_keyfile_name(r'C:\Users\Анд\PycharmProjects\sch1584bot\sch1584-53262c1690a5.json', scope)
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_classes (
            user_id INTEGER PRIMARY KEY,
            selected_classes TEXT
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

def save_user_classes(user_id, selected_classes):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_classes (user_id, selected_classes) VALUES (?, ?)
    ''', (user_id, selected_classes))
    conn.commit()
    conn.close()

def load_user_classes(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT selected_classes FROM user_classes WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Добавим функцию для создания таблицы user_classes
def create_user_classes_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_classes (
            user_id INTEGER PRIMARY KEY,
            selected_classes TEXT
        )
    ''')
    conn.commit()
    conn.close()

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
        types.InlineKeyboardButton(class_name, callback_data=f"class_{user_id}_{class_name}") for class_name in classes_for_parallel
    ]

    # Разбиваем кнопки по две в каждом столбце
    class_keyboard = types.InlineKeyboardMarkup(row_width=2)
    class_keyboard.add(*class_buttons)

    # Отправляем сообщение с Inline-клавиатурой для выбора класса
    bot.send_message(call.message.chat.id, "Выберите свой класс:", reply_markup=class_keyboard)


# Декоратор для обработки Inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('class_'))
def handle_class_selection(call):
    user_id = call.from_user.id
    selected_class = call.data.split('_')[2]

    # Обрабатываем выбор класса
    print(f"DEBUG: Пользователь {user_id} выбрал класс: {selected_class}")

    # Сохраняем выбранный класс в базе данных
    save_user_classes(user_id, selected_class)
    print(f"DEBUG: Класс пользователя {user_id} сохранен в базе данных")

    # Получаем список учеников для выбранного класса
    students_for_class = get_students_for_class(selected_class)
    print(f"DEBUG: Список учеников в классе {selected_class}: {students_for_class}")

    # Создаем кнопки для завершения регистрации и выбора еще одного класса
    finish_registration_button = types.InlineKeyboardButton("Завершить регистрацию",
                                                            callback_data=f"finish_registration_{user_id}")
    choose_another_class_button = types.InlineKeyboardButton("Выбрать еще один класс",
                                                             callback_data=f"choose_another_class_{user_id}")

    # Размещаем кнопки в одной строке
    keyboard = types.InlineKeyboardMarkup().row(finish_registration_button, choose_another_class_button)

    # Отправляем сообщение с кнопками
    bot.send_message(call.message.chat.id, "Выберите дальнейшее действие:", reply_markup=keyboard)


# Декоратор для обработки нажатий на кнопки "Завершить регистрацию" и "Выбрать еще один класс"
@bot.callback_query_handler(func=lambda call: call.data.startswith(('finish_registration_', 'choose_another_class_')))
def handle_additional_actions(call):
    user_id = call.from_user.id
    action = call.data.split('_')[0]

    if action == 'finish_registration':
        user_classes = load_user_classes(user_id)
        bot.send_message(call.message.chat.id, f"Регистрация завершена. Вы выбрали классы: {', '.join(user_classes)}")
    elif action == 'choose_another_class':
        choose_class(call.message)



# Добавим еще один декоратор для обработки нажатий на кнопки "Завершить регистрацию" и "Выбрать еще один класс"
@bot.callback_query_handler(func=lambda call: call.data.startswith(('finish_registration_', 'choose_another_class_')))
def handle_additional_actions(call):
    print("Handling additional actions")
    user_id = call.from_user.id
    action = call.data.split('_')[0]

    if action == 'finish_registration':
        print("Finishing registration")
        user_classes = load_user_classes(user_id)
        bot.send_message(call.message.chat.id, f"Регистрация завершена. Вы выбрали классы: {', '.join(user_classes)}")
    elif action == 'choose_another_class':
        print("Choosing another class")
        choose_class(call.message)


def get_students_for_classes(selected_classes):
    # Реализуйте логику получения списка учеников для выбранных классов
    pass


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
    print(f"DEBUG: Отправка списка учеников в классе {selected_class} пользователю {chat_id}")
    bot.send_message(chat_id, f"Список учеников в классе {selected_class}:\n" + "\n".join(students_for_class))

# Получение списка учеников для выбранного класса
def get_students_for_class(selected_class):
    class_column = worksheet.col_values(2)[1:]
    name_column = worksheet.col_values(1)[1:]

    # Получаем индексы учеников для выбранного класса
    indices = [i for i, class_name in enumerate(class_column) if class_name == selected_class]

    # Сортируем учеников по алфавиту на основе их индексов
    sorted_students = sorted([(name_column[i], i) for i in indices])

    # Возвращаем отсортированный список имен учеников
    return [student[0] for student in sorted_students]

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

def handle_mark_absence_single_class(chat_id, user_id, selected_class):
    # Получаем список учеников для выбранного класса
    students_for_class = get_students_for_class(selected_class)

    # Создаем кнопки для выбора причины отсутствия
    absence_reason_buttons = [
        types.InlineKeyboardButton("Отсутствует по болезни", callback_data=f"absence_illness_{user_id}"),
        types.InlineKeyboardButton("Отсутствует по семейным обстоятельствам", callback_data=f"absence_family_{user_id}"),
        types.InlineKeyboardButton("Придёт к ... уроку", callback_data=f"expected_time_{user_id}")
    ]

    # Разбиваем кнопки по две в каждом столбце
    absence_reason_keyboard = types.InlineKeyboardMarkup(row_width=2)
    absence_reason_keyboard.add(*absence_reason_buttons)

    # Отправляем сообщение с Inline-клавиатурой для выбора причины отсутствия
    bot.send_message(chat_id, "Выберите причину отсутствия:", reply_markup=absence_reason_keyboard)

# Декоратор для обработки текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    user_message = message.text.lower()

    # Логика обработки выбора времени при отсутствии
    if user_message.startswith("придет к "):
        handle_expected_time_selection(user_id, user_message)
    else:
        # Прочие случаи обрабатываем как выбор класса
        choose_class(message)

def handle_expected_time_selection(user_id, user_message):
    # Здесь можно обработать выбор времени и принять необходимые действия
    # Например, можно сохранить время в базе данных
    save_expected_time(user_id, user_message)

    # Отправляем сообщение об успешном выборе
    bot.send_message(user_id, f"Время прихода успешно установлено: {user_message}")

def choose_class_for_absence(message):
    chat_id = message.chat.id

    # Загружаем состояние пользователя (выбранные классы)
    user_classes = load_user_classes(message.from_user.id)

    # Создаем кнопки для выбора класса
    class_buttons = [
        types.InlineKeyboardButton(class_name, callback_data=f"{message.from_user.id}_{class_name}") for class_name in user_classes
    ]

    # Разбиваем кнопки по две в каждом столбце
    class_keyboard = types.InlineKeyboardMarkup(row_width=2)
    class_keyboard.add(*class_buttons)

    # Отправляем сообщение с Inline-клавиатурой для выбора класса
    bot.send_message(chat_id, "Выберите класс для отметки отсутствующих:", reply_markup=class_keyboard)

# Декоратор для обработки текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    user_message = message.text.lower()

    # Логика обработки выбора времени при отсутствии
    if user_message.startswith("придет к "):
        handle_expected_time_selection(user_id, user_message)
    else:
        # Прочие случаи обрабатываем как выбор класса
        choose_class(message)



# Запуск бота
if __name__ == "__main__":
    # Создаем таблицы в базе данных, если их нет
    create_tables()
    create_user_classes_table()  # Добавим вызов функции создания таблицы user_classes

    # Запуск бота
    bot.polling(none_stop=True)