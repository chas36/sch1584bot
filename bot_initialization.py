import os
from dotenv import load_dotenv
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# Инициализация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Подключение к Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(r"sch1584-dc1c7afa27e3.json", scope)
gc = gspread.authorize(credentials)

# ID вашей таблицы
spreadsheet_id = os.getenv('SPREADSHEET_ID')

# Откройте таблицу
worksheet = gc.open_by_key(spreadsheet_id).sheet1

# Получатели
RECIPIENT_CHAT_ID = os.getenv('RECIPIENT_CHAT_ID').split(',')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# Ключ доступа
ACCESS_KEY = os.getenv('ACCESS_KEY')

# Имя файла базы данных SQLite
DB_FILE = 'user_states.db'
