from telebot import types
import pytz
from datetime import datetime
from bot_initialization import bot, worksheet, RECIPIENT_CHAT_ID
from database import create_tables, load_user_states, save_user_state, get_users_with_classes, load_cache

absences = {}
# Глобальный словарь для хранения текущего класса пользователя
current_class_selection = {}
# Предположим, у нас есть словарь для хранения message_id сообщений, которые нужно будет удалить
messages_to_delete = {}

# Декоратор для обработки Inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('class_') or call.data == 'choose_class')
def handle_class_selection(call):
    print('handle_class_selection')
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
    print('handle_class_selection')
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
    print('get_students_for_class')
    data = load_cache()
    students = [(student['ID'], f"{student['FullName'].split()[0]} {student['FullName'].split()[1][0]}.{student['FullName'].split()[2][0]}.") for student in data if student['Класс'] == selected_class]
    return students

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
    # Создание Reply клавиатуры
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    # Добавление кнопки "Выбрать класс"
    markup.add(types.KeyboardButton("Выбрать класс"))

    # Приветственный текст
    welcome_text = (
        "Привет! Это бот школы 1584 для классных руководителей. Он предназначен для оповещения об отсутствующих учениках. "
        "Для начала использования, вам необходимо пройти регистрацию.\n\n"
        '''Для регистрации вам необходимо выбрать класс. <b>Для выбора класса необходимо написать "Выбрать класс" либо воспользоваться кнопкой внизу экрана</b>\n\n'''
        "Доступные команды:\n"
        "/help - получить список доступных команд\n\n"
        "По всем вопросам обращайтесь к @ascher_work"
    )

    # Отправляем приветственное сообщение
    bot.send_message(chat_id, welcome_text, parse_mode='HTML', reply_markup=markup)
    print(message.chat.id)  # Вывод chat_id в консоль


# Декоратор для обработки команды /help
@bot.message_handler(commands=['help'])
def help_command(message):
    print('help_command')
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
    print('my_classes')
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
    print('handle_confirm_selection')
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
# Обработчик текстовых сообщений для обработки нажатия кнопки "Выбрать класс"
@bot.message_handler(func=lambda message: message.text == "Выбрать класс")
def choose_class(message):
    print('choose_class')
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
    print('handle_parallel_selection')
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
    print('handle_text')
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
    print('send_reminders')
    users = get_users_with_classes()  # Получаем список пользователей с выбранными классами
    for user_id in users:
        markup = types.InlineKeyboardMarkup()
        reminder_button = types.InlineKeyboardButton("Отправить список отсутствующих", callback_data="send_absent_list")
        markup.add(reminder_button)
        bot.send_message(user_id, "Напоминание: Пожалуйста, отправьте список отсутствующих детей в выбранном классе.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "send_absent_list")
def handle_send_absent_list(call):
    print('handle_send_absent_list')
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
    print('show_classes_to_user')
    markup = types.InlineKeyboardMarkup()
    for user_class in user_classes:
        button = types.InlineKeyboardButton(user_class, callback_data=f"select_class_{user_class}")
        markup.add(button)
    # Добавляем кнопку "Отправить все списки"
    all_lists_button = types.InlineKeyboardButton("Отправить все списки", callback_data="send_all_lists")
    markup.add(all_lists_button)
    bot.send_message(chat_id, "Выберите класс или отправьте все списки отсутствующих:", reply_markup=markup)


def show_students_for_class(chat_id, selected_class):
    print('show_students_for_class')
    students = get_students_for_class(selected_class)  # Функция возвращает список кортежей (id, "Фамилия И.О.")
    markup = types.InlineKeyboardMarkup()

    # Создание кнопок для каждого ученика
    buttons = [types.InlineKeyboardButton(f"{name}", callback_data=f"absent_{student_id}") for student_id, name in students]
    while buttons:
        row = buttons[:2]  # Группируем по две кнопки в ряд
        markup.row(*row)
        buttons = buttons[2:]

    # Добавляем кнопку "Все присутствуют"
    all_present_button = types.InlineKeyboardButton("Все присутствуют", callback_data="all_present")
    markup.add(all_present_button)

    # Добавляем кнопку "Завершить список отсутствующих"
    finish_list_button = types.InlineKeyboardButton("Завершить список отсутствующих", callback_data="finish_absence_list")
    markup.add(finish_list_button)

    bot.send_message(chat_id, "Выберите отсутствующих учеников или нажмите 'Все присутствуют':", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "all_present")
def handle_all_present(call):
    print('handle_all_present')
    user_id = call.from_user.id
    selected_classes = load_user_states(user_id)
    if selected_classes:
        selected_class = selected_classes[0]  # Предполагается, что у пользователя только один класс

        # Обновление словаря absences, указывая, что отсутствующих нет
        absences[selected_class] = [{"name": "<i>Нет отсутствующих</i>", "reason": ""}]

        # Опционально: удаление предыдущих сообщений с кнопками
        # bot.delete_message(chat_id=call.message.chat.id, message_id=PREVIOUS_MESSAGE_ID)

        # Вызов функции finish_absence_list или отправка сообщения для ее вызова
        # Для прямого вызова:
        handle_finish_absence_list(call)

        # Если функция finish_absence_list ожидает другие параметры, адаптируйте вызов

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_class_'))
def handle_select_class(call):
    user_id = call.from_user.id
    class_name = call.data.split('select_class_')[1]
    current_class_selection[user_id] = class_name  # Сохраняем текущий выбранный класс
    show_students_for_class(call.message.chat.id, class_name)

@bot.callback_query_handler(func=lambda call: call.data.startswith('absent_'))
def handle_student_absent(call):
    print('handle_student_absent')
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

# Функция для добавления message_id в словарь
def add_message_to_delete(user_id, message_id):
    print('add_message_to_delete')
    if user_id not in messages_to_delete:
        messages_to_delete[user_id] = []
    messages_to_delete[user_id].append(message_id)

# Функция для удаления сообщений пользователя
def delete_user_messages(user_id):
    print('delete_user_messages')
    if user_id in messages_to_delete:
        for message_id in messages_to_delete[user_id]:
            try:
                bot.delete_message(chat_id=user_id, message_id=message_id)
            except Exception as e:
                print(f"Error deleting message: {e}")
        del messages_to_delete[user_id]  # Очистка списка после удаления
@bot.callback_query_handler(func=lambda call: call.data.startswith('reason_'))
def handle_absence_reason(call):
    print('handle_absence_reason')
    _, student_id, reason_code = call.data.split('_', 2)
    reason = reason_code.replace('_', ' ')
    student_name = get_student_name_by_id(student_id)
    class_name = get_class_by_student_id(student_id)

    if class_name not in absences:
        absences[class_name] = []

    absences[class_name].append({"name": student_name, "reason": reason})

    # Редактируем сообщение, обновляя текст и удаляя клавиатуру
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Отмечено отсутствие: {student_name} по причине '{reason}'",
        reply_markup=None
    )

def get_class_by_student_id(student_id):
    print('get_class_by_student_id')
    data = load_cache()
    for student in data:
        if str(student['ID']) == str(student_id):
            return student['Класс']
    return "Класс не найден"

# Функция для получения имени ученика по ID
def get_student_name_by_id(student_id):
    print('get_student_name_by_id')
    data = load_cache()
    for student in data:
        if str(student['ID']) == str(student_id):
            return f"{student['FullName'].split()[0]} {student['FullName'].split()[1][0]}.{student['FullName'].split()[2][0]}."
    return "Неизвестный ученик"


@bot.callback_query_handler(func=lambda call: call.data.startswith("come_to_lesson"))
def handle_come_to_lesson(call):
    print('handle_come_to_lesson')
    _, student_id = call.data.rsplit('_', 1)  # Используйте rsplit для корректной работы с student_id

    # Удаление предыдущего сообщения с кнопками
    try:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception as e:
        print(f"Error deleting message: {e}")

    # Создание новой клавиатуры с числами от 2 до 8
    lesson_numbers_markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for i in range(2, 8):
        lesson_button = types.InlineKeyboardButton(str(i), callback_data=f"lesson_{student_id}_{i}")
        buttons.append(lesson_button)

    lesson_numbers_markup.add(*buttons)  # Добавление всех кнопок сразу

    # Отправка нового сообщения с обновленной клавиатурой
    bot.send_message(call.message.chat.id, "Выберите, к какому уроку придет ученик:",
                     reply_markup=lesson_numbers_markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('lesson_'))
def handle_lesson_selection(call):
    print('handle_lesson_selection')
    _, student_id, lesson_number = call.data.split('_')
    student_name = get_student_name_by_id(student_id)  # Получение имени ученика
    class_name = get_class_by_student_id(student_id)  # Получение класса ученика

    # Формирование записи о том, что ученик придет к указанному уроку
    reason = f"Придет к {lesson_number} уроку"

    # Добавление записи в словарь absences
    if class_name not in absences:
        absences[class_name] = []
    absences[class_name].append({"name": student_name, "reason": reason})

    # Сообщение пользователю о сохранении информации
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Отмечено отсутствие: {student_name} Придет к {lesson_number} уроку",
        reply_markup=None  # Удаление клавиатуры
    )


# Обработчик для отметки ученика как отсутствующего
@bot.callback_query_handler(func=lambda call: call.data.startswith("absent_"))
def mark_student_absent(call):
    print('mark_student_absent')
    _, student_id, reason = call.data.split('_')
    student_name = get_student_name_by_id(student_id)  # Предполагаемая функция для получения имени ученика
    class_name = get_class_by_student_id(student_id)  # Предполагаемая функция для получения класса ученика

    # Добавление ученика в список отсутствующих
    if class_name not in absences:
        absences[class_name] = []

    absences[class_name].append((student_name, reason))

    # Сортировка списка отсутствующих в классе
    absences[class_name] = sorted(absences[class_name], key=lambda x: x[0])


@bot.callback_query_handler(func=lambda call: call.data == "finish_absence_list")
def handle_finish_absence_list(call):
    print("handle_finish_absence_list")
    user_id = call.from_user.id

    selected_classes = load_user_states(user_id)
    if selected_classes:
        if len(selected_classes) > 1:
            # Если у пользователя несколько классов, снова показываем список классов
            show_classes_to_user(call.message.chat.id, selected_classes)
        else:
            # Если у пользователя один класс, используем его напрямую
            selected_class = selected_classes[0]  # Прямое использование первого и единственного класса
            if selected_class in absences and absences[selected_class]:
                send_absence_list_to_recipient(selected_class, absences[selected_class])
                bot.send_message(call.message.chat.id, "Список отсутствующих учеников успешно отправлен.")
                # После отправки можно очистить запись для этого пользователя
                if user_id in current_class_selection:
                    del current_class_selection[user_id]
            else:
                bot.send_message(call.message.chat.id, "Список отсутствующих учеников пуст.")
    else:
        bot.send_message(call.message.chat.id, "Класс для пользователя не найден.")

@bot.callback_query_handler(func=lambda call: call.data == "send_all_lists")
def handle_send_all_lists(call):
    user_id = call.from_user.id
    selected_classes = load_user_states(user_id)
    # Отправляем списки отсутствующих для всех выбранных классов
    for selected_class in selected_classes:
        if selected_class in absences and absences[selected_class]:
            send_absence_list_to_recipient(selected_class, absences[selected_class])
        else:
            bot.send_message(call.message.chat.id, f"Список отсутствующих учеников в классе {selected_class} пуст.")
    # После отправки всех списков, можно уведомить пользователя
    bot.send_message(call.message.chat.id, "Все списки отсутствующих успешно отправлены.")

def send_absence_list_to_recipient(selected_class, absence_list):
    # Сортировка списка отсутствующих учеников по алфавиту по имени
    sorted_absence_list = sorted(absence_list, key=lambda x: x['name'])
    # Формирование и отправка сообщения
    message_text = f"<b>{selected_class}</b>, список отсутствующих:\n"
    for student in sorted_absence_list:
        message_text += f"{student['name']} - {student['reason']}\n"
    if not sorted_absence_list:
        message_text = f"Класс {selected_class}, отсутствующих учеников нет."
    bot.send_message(RECIPIENT_CHAT_ID, message_text, parse_mode='HTML')

    print(message_text)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    print(echo_all)
    print(message.chat.id)  # Вывод chat_id в консоль
    bot.reply_to(message, f"Ваш chat_id: {message.chat.id}")

# Отправка сообщения всем пользователям при запуске бота
if __name__ == "__main__":
    # Создаем таблицы в базе данных, если их нет
    create_tables()

    send_reminders()


    bot.polling(none_stop=True)