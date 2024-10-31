import telebot
from telebot import types
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

# Настройка базы данных
conn = sqlite3.connect("user_data.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для хранения данных пользователя
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_data (
    user_id INTEGER PRIMARY KEY,
    goal TEXT,
    age INTEGER,
    gender TEXT,
    weight INTEGER,
    height INTEGER
)
''')
conn.commit()

# Словарь для отслеживания этапов опроса пользователя
user_stage = {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id

    # Добавляем пользователя в базу данных, если его нет
    cursor.execute("INSERT OR IGNORE INTO user_data (user_id) VALUES (?)", (user_id,))
    conn.commit()

    # Отправляем приветственное сообщение и предлагаем выбрать цель
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Потеря веса"),
                 types.KeyboardButton("Поддержание веса"),
                 types.KeyboardButton("Набор веса"))

    bot.send_message(message.chat.id, "Здравствуйте, я бот-диетолог, хотел бы узнать цель вашей диеты", reply_markup=keyboard)
    user_stage[user_id] = 'goal'  # Устанавливаем начальный этап



# Команда для расчета калорий
@bot.message_handler(commands=['calories'])
def calculate_calories(message):
    user_id = message.from_user.id
    cursor.execute("SELECT goal, age, gender, weight, height FROM user_data WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        bot.send_message(message.chat.id, "Пожалуйста, завершите регистрацию, чтобы воспользоваться этой командой.")
        return

    goal, age, gender, weight, height = user_data

    # Формула Харриса-Бенедикта для расчета базового метаболизма (BMR)
    if gender == "Мужской":
        bmr = 88.36 + (13.4 * weight) + (4.8 * height) - (5.7 * age)
    else:
        bmr = 447.6 + (9.2 * weight) + (3.1 * height) - (4.3 * age)

    # Учет цели
    if goal == "Потеря веса":
        calories_needed = bmr * 0.8  # Снижение калорийности для похудения
    elif goal == "Набор веса":
        calories_needed = bmr * 1.2  # Увеличение калорийности для набора массы
    else:
        calories_needed = bmr  # Поддержание веса

    bot.send_message(message.chat.id,
                     f"Для вашей цели вам нужно потреблять примерно {int(calories_needed)} калорий в день.")


# Команда для расчета потребности в воде
@bot.message_handler(commands=['water'])
def calculate_water(message):
    user_id = message.from_user.id
    cursor.execute("SELECT weight FROM user_data WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if not result:
        bot.send_message(message.chat.id, "Пожалуйста, завершите регистрацию, чтобы воспользоваться этой командой.")
        return

    weight = result[0]
    # Общая рекомендация: 30 мл воды на 1 кг веса
    water_needed = weight * 0.03  # в литрах
    glasses_needed = water_needed / 0.25  # 1 стакан = 250 мл

    bot.send_message(message.chat.id, f"Вам нужно пить примерно {int(glasses_needed)} стаканов воды в день.")


# Команда для расчета потребности во сне
@bot.message_handler(commands=['sleep'])
def calculate_sleep(message):
    user_id = message.from_user.id
    cursor.execute("SELECT age FROM user_data WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if not result:
        bot.send_message(message.chat.id, "Пожалуйста, завершите регистрацию, чтобы воспользоваться этой командой.")
        return

    age = result[0]

    # Рекомендации по сну в зависимости от возраста
    if age < 18:
        sleep_hours = 8.5
    elif 18 <= age <= 64:
        sleep_hours = 7.0
    else:
        sleep_hours = 7.5

    bot.send_message(message.chat.id, f"Для вашего возраста рекомендуется спать около {sleep_hours} часов в сутки.")

# Обработчик сообщений для разных этапов
@bot.message_handler(func=lambda message: True)
def handle_response(message):
    user_id = message.from_user.id
    stage = user_stage.get(user_id)

    # Этап: выбор цели
    if stage == 'goal':
        goal = message.text
        if goal in ["Потеря веса", "Поддержание веса", "Набор веса"]:
            cursor.execute("UPDATE user_data SET goal = ? WHERE user_id = ?", (goal, user_id))
            conn.commit()

            bot.send_message(message.chat.id, "Введите Ваш возраст", reply_markup=types.ReplyKeyboardRemove())
            user_stage[user_id] = 'age'
        else:
            bot.send_message(message.chat.id, "Пожалуйста, выберите цель, используя кнопки.")

    # Этап: ввод возраста
    elif stage == 'age':
        if message.text.isdigit():
            age = int(message.text)
            cursor.execute("UPDATE user_data SET age = ? WHERE user_id = ?", (age, user_id))
            conn.commit()

            # Клавиатура для выбора пола
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(types.KeyboardButton("Мужской"), types.KeyboardButton("Женский"))

            bot.send_message(message.chat.id, "Введите Ваш пол", reply_markup=keyboard)
            user_stage[user_id] = 'gender'
        else:
            bot.send_message(message.chat.id, "Пожалуйста, введите корректный возраст.")

    # Этап: выбор пола
    elif stage == 'gender':
        gender = message.text
        if gender in ["Мужской", "Женский"]:
            cursor.execute("UPDATE user_data SET gender = ? WHERE user_id = ?", (gender, user_id))
            conn.commit()

            bot.send_message(message.chat.id, "Введите Ваш вес", reply_markup=types.ReplyKeyboardRemove())
            user_stage[user_id] = 'weight'
        else:
            bot.send_message(message.chat.id, "Пожалуйста, выберите пол, используя кнопки.")

    # Этап: ввод веса
    elif stage == 'weight':
        if message.text.isdigit():
            weight = int(message.text)
            cursor.execute("UPDATE user_data SET weight = ? WHERE user_id = ?", (weight, user_id))
            conn.commit()

            bot.send_message(message.chat.id, "Введите Ваш рост")
            user_stage[user_id] = 'height'
        else:
            bot.send_message(message.chat.id, "Пожалуйста, введите корректный вес.")

    # Этап: ввод роста
    elif stage == 'height':
        if message.text.isdigit():
            height = int(message.text)
            cursor.execute("UPDATE user_data SET height = ? WHERE user_id = ?", (height, user_id))
            conn.commit()

            bot.send_message(message.chat.id, "Спасибо! Ваши данные сохранены.")
            user_stage.pop(user_id)  # Очищаем этап пользователя
        else:
            bot.send_message(message.chat.id, "Пожалуйста, введите корректный рост.")


# Запуск бота
bot.polling()
