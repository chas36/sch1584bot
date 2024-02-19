import sqlite3
from telebot import types
#from telegram import InlineKeyboardButton, InlineKeyboardMarkup
#from telegram.ext import CallbackQueryHandler
from bot_initialization import bot, gc, spreadsheet_id, worksheet,RECIPIENT_CHAT_ID
from database import create_tables, load_user_states, save_user_state, get_users_with_classes

# Имя файла базы данных SQLite
DB_FILE = 'user_states.db'

absences = {}

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
    students = get_students_for_class(
        selected_class)  # Допустим, функция возвращает список кортежей (id, "Фамилия И.О.")
    markup = types.InlineKeyboardMarkup()

    # Создаем кнопки для каждого ученика и группируем по две в ряд
    buttons = [types.InlineKeyboardButton(f"{name}", callback_data=f"absent_{student_id}") for student_id, name in
               students]
    while buttons:
        row = buttons[:2]  # Берем первые две кнопки для текущего ряда
        markup.row(*row)  # Добавляем ряд в клавиатуру
        buttons = buttons[2:]  # Удаляем добавленные кнопки из списка

    # Добавляем кнопку "Все присутствуют" в новый ряд
    all_present_button = types.InlineKeyboardButton("Все присутствуют", callback_data="all_present")
    markup.add(all_present_button)

    bot.send_message(chat_id, "Выберите отсутствующих учеников или нажмите 'Все присутствуют':", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "all_present")
def handle_all_present(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Отмечено, что все ученики присутствуют.",
        reply_markup=None  # Удаление клавиатуры
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_class_'))
def handle_select_class(call):
    class_name = call.data.split('select_class_')[1]
    show_students_for_class(call.message.chat.id, class_name)

@bot.callback_query_handler(func=lambda call: call.data.startswith('absent_'))
def handle_student_absent(call):
    student_id = call.data.split('_')[1]
    student_name = get_student_name_by_id(student_id)  # Получите имя ученика по ID
    class_name = get_class_by_student_id(student_id)  # Получите класс ученика по ID

    # Инициализация записи для класса, если еще не существует
    if class_name not in absences:
        absences[class_name] = []

    markup = types.InlineKeyboardMarkup()
    come_to_lesson_button = types.InlineKeyboardButton("Придет к ... уроку", callback_data=f"come_to_lesson_{student_id}")
    reasons = ["Семейные обстоятельства", "По болезни"]
    # Разбиваем список причин на пары для добавления в ряды
    reason_pairs = [reasons[i:i + 2] for i in range(0, len(reasons), 2)]
    for pair in reason_pairs:
        row_buttons = [
            types.InlineKeyboardButton(reason, callback_data=f"reason_{student_id}_{reason.replace(' ', '_')}") for
            reason in pair]
        markup.row(*row_buttons)
        markup.add(come_to_lesson_button)
    bot.send_message(call.message.chat.id,
                     f"Вы хотите отметить отсутствие ученика {student_name} Выберите причину отсутствия:",
                     reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reason_'))
def handle_absence_reason(call):
    _, student_id, reason_code = call.data.split('_', 2)
    reason = reason_code.replace('_', ' ')  # Восстанавливаем причину отсутствия из кода
    student_name = get_student_name_by_id(student_id)  # Получаем имя ученика по его ID

    # Редактируем сообщение, обновляя текст и удаляя клавиатуру
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Отмечено отсутствие: {student_name} по причине '{reason}'",
        reply_markup=None
    )

def get_class_by_student_id(student_id):
    rows = worksheet.get_all_values()
    for row in rows[1:]:  # Пропускаем заголовок
        if row[2] == str(student_id):  # ID ученика находится в третьем столбце (индекс 2)
            return row[1]  # Класс ученика находится во втором столбце (индекс 1)
    return "Класс не найден"

# Функция для получения имени ученика по ID
def get_student_name_by_id(student_id):
    student_records = worksheet.get_all_records()  # Получаете все записи с листа

    for record in student_records:
        if str(record['ID']) == str(student_id):  # Предполагается, что у вас есть колонка ID
            full_name = record['FullName']  # И колонка FullName с полным именем ученика
            name_parts = full_name.split()
            if len(name_parts) == 3:
                return f"{name_parts[0]} {name_parts[1][0]}.{name_parts[2][0]}."  # Преобразование в "Фамилия И.О."
    return "Неизвестный ученик"


@bot.callback_query_handler(func=lambda call: call.data.startswith("come_to_lesson"))
def handle_come_to_lesson(call):
    _, student_id = call.data.rsplit('_', 1)  # Используйте rsplit для корректной работы с student_id
    lesson_numbers_markup = types.InlineKeyboardMarkup()
    for i in range(2, 8):
        lesson_button = types.InlineKeyboardButton(str(i), callback_data=f"lesson_{student_id}_{i}")
        lesson_numbers_markup.add(lesson_button)

    # Обновите сообщение или отправьте новое с обновленной клавиатурой
    bot.send_message(call.message.chat.id, "Выберите, к какому уроку придет ученик:",
                     reply_markup=lesson_numbers_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lesson_'))
def handle_lesson_selection(call):
    _, student_id, lesson_number = call.data.split('_')
    student_name = get_student_name_by_id(student_id)  # Используйте вашу реализацию этой функции
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Отмечено отсутствие: {student_name} Придет к {lesson_number} уроку",
        reply_markup=None  # Удаление клавиатуры
    )
@bot.callback_query_handler(func=lambda call: call.data.startswith("lesson_"))
def handle_lesson_selection(call):
    selected_lesson = call.data.split("_")[1]  # Извлечение номера урока из callback_data
    user_id = call.from_user.id
    # Сохраняем информацию об отсутствии с указанием выбранного урока (реализуйте эту функцию)
    save_absence_info(user_id, f"Придет к {selected_lesson} уроку")

    # Отправляем подтверждение пользователю
    bot.send_message(call.message.chat.id, f"Записано: придет к {selected_lesson} уроку.")


def handle_absence(student_id, reason):
    # Обработка отсутствия по выбранной причине
    print(f"Ученик {get_student_name_by_id(student_id)} отсутствует по причине: {reason}")
    # Здесь можно добавить логику записи в базу данных или другие действия

def handle_absence_with_lesson(student_id, lesson_number):
    # Обработка отсутствия ученика с указанием номера урока
    print(f"Ученик {get_student_name_by_id(student_id)} придет к {lesson_number} уроку")
    # Здесь также можно добавить логику записи в базу данных или другие действия

def send_absence_list_to_recipient(absence_list):
    # Формирование сообщения
    message_text = '\n'.join([f"{student['name']} {student['reason']}" for student in absence_list])
    bot.send_message(RECIPIENT_CHAT_ID, message_text)

# Отправка сообщения всем пользователям при запуске бота
if __name__ == "__main__":
    # Создаем таблицы в базе данных, если их нет
    create_tables()

    send_reminders()

    bot.polling(none_stop=True)