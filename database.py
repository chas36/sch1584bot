import sqlite3
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
