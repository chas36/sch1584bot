import sqlite3
from telebot import types
#from telegram import InlineKeyboardButton, InlineKeyboardMarkup
#from telegram.ext import CallbackQueryHandler
from bot_initialization import bot, gc, spreadsheet_id, worksheet
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
def get_students_for_class(selected_class):
    class_column = worksheet.col_values(2)[1:]  # Классы находятся во втором столбце
    full_name_column = worksheet.col_values(1)[1:]  # Полные имена учеников в первом столбце
    user_id_column = worksheet.col_values(3)[1:]  # ID пользователя в третьем столбце

    students = []
    for full_name, class_name, user_id in zip(full_name_column, class_column, user_id_column):
        if class_name == selected_class:
            name_parts = full_name.split()  # Разделяем полное имя на части
            if len(name_parts) == 3:  # Убедимся, что есть фамилия, имя и отчество
                short_name = f"{name_parts[0]} {name_parts[1][0]}.{name_parts[2][0]}."  # Сокращаем до "Фамилия И.О."
                students.append((user_id, short_name))  # Сначала идентификатор, потом "Фамилия И.О."
            else:
                students.append((full_name, user_id))  # Если формат отличается, используем полное имя

    return students

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

def send_reminders():
    users = get_users_with_classes()  # Получаем список пользователей с выбранными классами
    for user_id in users:
        markup = types.InlineKeyboardMarkup()
        reminder_button = types.InlineKeyboardButton("Отправить список отсутствующих", callback_data="send_absent_list")
        markup.add(reminder_button)
        bot.send_message(user_id, "Напоминание: Пожалуйста, отправьте список отсутствующих детей в выбранном классе.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "send_absent_list")
def handle_send_absent_list(call):
    user_id = call.from_user.id
    user_classes = load_user_states(user_id)
    if len(user_classes) > 1:
        # Показываем кнопки со всеми классами пользователя
        show_classes_to_user(call.message.chat.id, user_classes)
    elif len(user_classes) == 1:
        # Показываем список учеников одного класса
        show_students_for_class(call.message.chat.id, user_classes[0])
    else:
        bot.answer_callback_query(call.id, "У вас нет выбранных классов.")

def show_classes_to_user(chat_id, user_classes):
    markup = types.InlineKeyboardMarkup()
    for user_class in user_classes:
        button = types.InlineKeyboardButton(user_class, callback_data=f"class_{user_class}")
        markup.add(button)
    bot.send_message(chat_id, "Выберите класс:", reply_markup=markup)

def show_students_for_class(chat_id, selected_class):
    students = get_students_for_class(selected_class)  # Должна возвращать список кортежей (id, "Фамилия И.О.")
    markup = types.InlineKeyboardMarkup()
    for student_id, short_name in students:
        # Используйте short_name для текста кнопки, а student_id для callback_data
        button = types.InlineKeyboardButton(short_name, callback_data=f"absent_{student_id}")
        markup.add(button)
    bot.send_message(chat_id, "Отметьте отсутствующих учеников:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_class_'))
def handle_select_class(call):
    class_name = call.data.split('select_class_')[1]
    show_students_for_class(call.message.chat.id, class_name)

# Отправка сообщения всем пользователям при запуске бота
if __name__ == "__main__":
    # Создаем таблицы в базе данных, если их нет
    create_tables()

    send_reminders()

    bot.polling(none_stop=True)