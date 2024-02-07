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
credentials = ServiceAccountCredentials.from_json_keyfile_name(r"C:\Users\Пользователь\PycharmProjects\sch1584bot\sch1584-0b47bcc851fb.json", scope)

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
            user_id INTEGER,
            selected_class TEXT,
            PRIMARY KEY (user_id, selected_class)
        )
    ''')
    conn.commit()
    conn.close()

# Функция для загрузки всех выбранных классов для пользователя
def load_user_states(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT selected_class FROM user_states WHERE user_id = ?
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return [result[0] for result in results] if results else []

# Ваша существующая функция для сохранения состояния пользователя
def save_user_state(user_id, selected_class):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_states (user_id, selected_class) VALUES (?, ?)
    ''', (user_id, selected_class))
    conn.commit()
    conn.close()

# Декоратор для обработки Inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('class_') or call.data == 'choose_class')
def handle_class_selection(call):
    user_id = call.from_user.id

    # Если нажата кнопка "Выбрать еще один класс", вызываем функцию выбора класса
    if call.data == 'choose_class':
        choose_class(call.message)
    else:
        # Если выбран конкретный класс, создаем кнопки для подтверждения и выбора еще одного класса
        selected_class = call.data.split('_')[1]

        confirm_button = types.InlineKeyboardButton("Подтвердить выбор", callback_data=f"confirm_{selected_class}")
        choose_another_button = types.InlineKeyboardButton("Выбрать еще один класс", callback_data="choose_class")

        confirm_keyboard = types.InlineKeyboardMarkup(row_width=2)
        confirm_keyboard.add(confirm_button, choose_another_button)

        # Сохраняем состояние пользователя (выбранный класс)
        save_user_state(user_id, selected_class)

        # Отправляем сообщение с клавиатурой для подтверждения выбора
        bot.send_message(call.message.chat.id, f"Вы выбрали класс: {selected_class}", reply_markup=confirm_keyboard)

# Логика обработки выбора класса
def handle_class_selection(chat_id, user_id):
    # Получаем список всех выбранных классов для данного пользователя
    selected_classes = load_user_states(user_id)

    if selected_classes:
        # Формируем сообщение с перечислением выбранных классов
        message_text = f"Ваши текущие классы:\n" + "\n".join(selected_classes)
        bot.send_message(chat_id, message_text)
    else:
        bot.send_message(chat_id, "Вы еще не выбрали ни одного класса.")


# Получение списка учеников для выбранных классов
def get_students_for_classes(selected_classes):
    class_column = worksheet.col_values(2)[1:]
    name_column = worksheet.col_values(1)[1:]

    students_for_classes = [name_column[i] for i in range(len(class_column)) if class_column[i] in selected_classes]
    return students_for_classes

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

def get_students_for_class(selected_class):
    class_column = worksheet.col_values(2)[1:]
    name_column = worksheet.col_values(1)[1:]

    # Получаем индексы учеников для выбранного класса
    indices = [i for i, class_name in enumerate(class_column) if class_name == selected_class]

    # Сортируем учеников по алфавиту на основе их индексов
    sorted_students = sorted([(name_column[i], i) for i in indices])

    # Возвращаем отсортированный список имен учеников
    return [student[0] for student in sorted_students]

# Декоратор для команды "/my_classes"
@bot.message_handler(commands=['my_classes'])
def my_classes(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Загружаем состояние пользователя (выбранные классы)
    selected_classes = load_user_states(user_id)

    if selected_classes:
        bot.send_message(chat_id, f"Ваши выбранные классы: {', '.join(selected_classes)}")
    else:
        bot.send_message(chat_id, "Вы еще не выбрали ни одного класса. Используйте /choose_class.")


# Декоратор для обработки подтверждения выбора
@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def handle_confirm_selection(call):
    user_id = call.from_user.id
    selected_class = call.data.split('_')[1]

    # Сохраняем состояние пользователя (выбранный класс)
    save_user_state(user_id, selected_class)

    # Отправляем сообщение о подтверждении выбора
    selected_classes = load_user_states(user_id)
    if selected_classes:
        classes_message = "\n".join(selected_classes)
        bot.send_message(call.message.chat.id, f"Ваши классы:\n{classes_message}\nВыбор подтвержден!")
    else:
        bot.send_message(call.message.chat.id, "Ни один класс не выбран. Выберите класс снова.")


# Декоратор для команды "choose_class"
@bot.message_handler(commands=['choose_class'])
def choose_class(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Загружаем состояние пользователя (выбранную параллель и класс)
    selected_classes = load_user_states(user_id)


    if selected_classes:
        # Если есть выбранная параллель, показываем ее
        bot.send_message(chat_id, f"Ваша текущая параллель: {selected_parallel}")
        # Получаем список уникальных классов для выбранной параллели
        class_column = worksheet.col_values(2)[1:]
        classes_for_parallel = sorted(set(class_name for class_name in class_column if class_name.startswith(selected_parallel)))

        # Создаем кнопки для выбора класса
        class_buttons = [
            types.InlineKeyboardButton(class_name, callback_data=f"class_{class_name}") for class_name in classes_for_parallel
        ]

        # Разбиваем кнопки по две в каждом столбце
        class_keyboard = types.InlineKeyboardMarkup(row_width=2)
        class_keyboard.add(*class_buttons)

        # Отправляем сообщение с Inline-клавиатурой для выбора класса
        bot.send_message(chat_id, "Выберите свой класс:", reply_markup=class_keyboard)
    else:
        # Если параллель не выбрана, предлагаем выбрать параллель
        # Создаем кнопки для выбора параллели
        parallel_buttons = [
            types.InlineKeyboardButton(str(i), callback_data=f"parallel_{i}") for i in range(5, 12)
        ]

        # Разбиваем кнопки по две в каждом столбце
        parallel_keyboard = types.InlineKeyboardMarkup(row_width=2)
        parallel_keyboard.add(*parallel_buttons)

        # Отправляем сообщение с Inline-клавиатурой для выбора параллели
        bot.send_message(chat_id, "Выберите свою параллель:", reply_markup=parallel_keyboard)


# Декоратор для обработки выбора параллели
@bot.callback_query_handler(func=lambda call: call.data.startswith('parallel_'))
def handle_parallel_selection(call):
    user_id = call.from_user.id
    selected_parallel = call.data.split('_')[1]

    # Сохраняем состояние пользователя (выбранную параллель)
    #save_user_state(user_id, selected_parallel)

    # Получаем список уникальных классов для выбранной параллели
    class_column = worksheet.col_values(2)[1:]
    classes_for_parallel = sorted(set(class_name for class_name in class_column if class_name.startswith(selected_parallel)))

    # Создаем кнопки для выбора класса
    class_buttons = [
        types.InlineKeyboardButton(class_name, callback_data=f"class_{class_name}") for class_name in classes_for_parallel
    ]

    # Разбиваем кнопки по две в каждом столбце
    class_keyboard = types.InlineKeyboardMarkup(row_width=2)
    class_keyboard.add(*class_buttons)

    # Отправляем сообщение с Inline-клавиатурой для выбора класса
    bot.send_message(call.message.chat.id, "Выберите свой класс:", reply_markup=class_keyboard)


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


# Получение списка всех пользователей с выбранными классами
def get_users_with_classes():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM user_states")
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

# Отправка сообщения всем пользователям
def send_reminder_to_users(message):
    users = get_users_with_classes()
    for user_id in users:
        bot.send_message(user_id, message)



# Отправка напоминания всем пользователям при запуске бота
if __name__ == "__main__":
    reminder_message = "Напоминание: Пожалуйста, отправьте список отсутствующих детей в выбранном классе."
    send_reminder_to_users(reminder_message)
    bot.polling(none_stop=True)
