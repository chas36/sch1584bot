import sqlite3
from telebot import types
#from telegram import InlineKeyboardButton, InlineKeyboardMarkup
#from telegram.ext import CallbackQueryHandler
from bot_initialization import bot, gc, spreadsheet_id,worksheet
from database import create_tables, load_user_states, save_user_state, get_users_with_classes

# Имя файла базы данных SQLite
DB_FILE = 'user_states.db'

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

# Отправка сообщения всем пользователям
def send_reminder_to_users(message):
    users = get_users_with_classes()
    for user_id in users:
        bot.send_message(user_id, message)

# Декоратор для команды /send_absent_list
@bot.message_handler(commands=['send_absent_list'])
def send_absent_list(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Получаем список классов пользователя
    user_classes = get_user_classes(user_id)

    if len(user_classes) == 1:
        # Если у пользователя один класс, отображаем список учеников этого класса с возможностью отметки отсутствующих
        class_name = user_classes[0]
        students = get_students_for_class(class_name)
        keyboard = generate_absent_list_keyboard(students)
        bot.send_message(chat_id, f"Выберите отсутствующих учеников в классе {class_name}:", reply_markup=keyboard)
    elif len(user_classes) > 1:
        # Если у пользователя несколько классов, отображаем кнопки со всеми его классами для выбора
        keyboard = generate_class_selection_keyboard(user_classes)
        bot.send_message(chat_id, "Выберите класс:", reply_markup=keyboard)
    else:
        bot.send_message(chat_id, "У вас нет выбранных классов.")

# Генерация клавиатуры для выбора класса
def generate_class_selection_keyboard(classes):
    keyboard = types.InlineKeyboardMarkup()
    for class_name in classes:
        button = types.InlineKeyboardButton(class_name, callback_data=f"select_class_{class_name}")
        keyboard.add(button)
    return keyboard

# Обработчик для выбора класса
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_class_'))
def handle_class_selection(call):
    user_id = call.from_user.id
    selected_class = call.data.split('_')[1]

    # Получаем список учеников выбранного класса с возможностью отметки отсутствующих
    students = get_students_for_class(selected_class)
    keyboard = generate_absent_list_keyboard(students)

    # Отправляем сообщение с возможностью отметки отсутствующих учеников
    bot.send_message(call.message.chat.id, f"Выберите отсутствующих учеников в классе {selected_class}:", reply_markup=keyboard)

# Генерация клавиатуры для отметки отсутствующих учеников
def generate_absent_list_keyboard(students):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for student in students:
        button = types.InlineKeyboardButton(student, callback_data=f"mark_absent_{student}")
        keyboard.add(button)
    return keyboard

# Обработчик для отметки отсутствующего ученика
@bot.callback_query_handler(func=lambda call: call.data.startswith('mark_absent_'))
def handle_mark_absent(call):
    student_name = call.data.split('_')[1]
    # Здесь можно добавить логику для отметки отсутствующего ученика, например, запись в базу данных или отправку уведомления

    # Отправляем сообщение об успешной отметке
    bot.answer_callback_query(callback_query_id=call.id, text=f"{student_name} отмечен как отсутствующий.")


# Отправка сообщения всем пользователям при запуске бота
if __name__ == "__main__":
    # Создаем таблицы в базе данных, если их нет
    create_tables()

    reminder_message = "Напоминание: Пожалуйста, отправьте список отсутствующих детей в выбранном классе."

    send_reminder_to_users(reminder_message)
    bot.polling(none_stop=True)