from oauth2client.service_account import ServiceAccountCredentials
import telebot
import gspread

bot = telebot.TeleBot('6332665358:AAHXpmnyWO4yKza0GAvgcy6nCFVwETs1aaA')

# Подключение к Google Sheets
scope = 'https://spreadsheets.google.com/feeds https://www.googleapis.com/auth/drive'
credentials = ServiceAccountCredentials.from_json_keyfile_name(r'C:\Users\Анд\PycharmProjects\sch1584bot\sch1584-53262c1690a5.json', scope)
gc = gspread.authorize(credentials)

# ID вашей таблицы
spreadsheet_id = '1dA-RLiyEI3MtV5uFNvEIGG913b_HtAy18gGxkXt1JWI'

# ID вашей таблицы
spreadsheet_id = '1dA-RLiyEI3MtV5uFNvEIGG913b_HtAy18gGxkXt1JWI'
# Откройте таблицу
worksheet = gc.open_by_key(spreadsheet_id).sheet1  # Предполагается, что данные в первом листе

RECIPIENT_CHAT_ID = '264739491'