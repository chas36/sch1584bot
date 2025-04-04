import sqlite3
import json
from bot_initialization import worksheet

# Имя файла базы данных SQLite
DB_FILE = 'user_states.db'


def create_tables():
  print('create_tables')
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
  print('load_user_states')
  """Загрузка всех выбранных классов для пользователя"""
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      '''
        SELECT selected_class FROM user_states WHERE user_id = ?
    ''', (user_id, ))
  results = cursor.fetchall()
  conn.close()
  return [result[0] for result in results] if results else []


# Ваша существующая функция для сохранения состояния пользователя
def save_user_state(user_id, selected_class):
  print('save_user_state')
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      '''
        INSERT OR REPLACE INTO user_states (user_id, selected_class) VALUES (?, ?)
    ''', (user_id, selected_class))
  conn.commit()
  conn.close()


# Получение списка всех пользователей с выбранными классами
def get_users_with_classes():
  print('get_users_with_classes')
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("SELECT DISTINCT user_id FROM user_states")
  users = cursor.fetchall()
  print("Users with classes:",
        [user[0] for user in users])  # Добавляем логирование для отладки
  conn.close()
  return [user[0] for user in users]


def fetch_data_from_sheets():
  print('fetch_data_from_sheets')
  data = worksheet.get_all_records()
  return data


def initialize_db():
  print('initialize_db')
  conn = sqlite3.connect('cache.db')
  c = conn.cursor()
  # Создаем таблицу, если она еще не существует
  c.execute(
      '''CREATE TABLE IF NOT EXISTS cache (id INTEGER PRIMARY KEY, data TEXT)'''
  )
  conn.commit()
  conn.close()


def update_cache(data):
  print('update_cache')
  conn = sqlite3.connect('cache.db')
  c = conn.cursor()
  # Сохраняем данные в формате JSON в таблице cache
  c.execute('INSERT OR REPLACE INTO cache (id, data) VALUES (1, ?)',
            (json.dumps(data), ))
  conn.commit()
  conn.close()


def load_cache():
  conn = sqlite3.connect('cache.db')
  c = conn.cursor()
  c.execute("SELECT data FROM cache WHERE id = 1")
  data = c.fetchone()[0]
  conn.close()
  return json.loads(data)


def save_access_key_state(user_id, state):
    print('save_access_key_state')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_key_states (
            user_id INTEGER PRIMARY KEY,
            has_access INTEGER
        )
    ''')
    cursor.execute('''
        INSERT OR REPLACE INTO access_key_states (user_id, has_access) VALUES (?, ?)
    ''', (user_id, int(state)))
    conn.commit()
    conn.close()

def load_access_key_state(user_id):
    print('load_access_key_state')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_key_states (
            user_id INTEGER PRIMARY KEY,
            has_access INTEGER
        )
    ''')
    cursor.execute('SELECT has_access FROM access_key_states WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result[0]) if result else False

initialize_db()
data = fetch_data_from_sheets()
update_cache(data)
