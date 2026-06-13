import telebot
import requests
import re
from datetime import datetime
import random
import os

# ==========================================
# ТОКЕНИ БЕРУТЬСЯ З ЗМІННИХ СЕРЕДОВИЩА (Render)
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')
# ==========================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

SYSTEM_PROMPT = "Ти — Nelox AI, україномовний асистент. Твій творець — Діма Марущак. Відповідай ТІЛЬКИ українською. НЕ використовуй теги <think>."

REGIONS = {
    "вінницька": "Вінниця", "волинська": "Луцьк", "дніпропетровська": "Дніпро",
    "донецька": "Краматорськ", "житомирська": "Житомир", "закарпатська": "Ужгород",
    "запорізька": "Запоріжжя", "івано-франківська": "Івано-Франківськ", "київська": "Київ",
    "кіровоградська": "Кропивницький", "луганська": "Сєвєродонецьк", "львівська": "Львів",
    "миколаївська": "Миколаїв", "одеська": "Одеса", "полтавська": "Полтава",
    "рівненська": "Рівне", "сумська": "Суми", "тернопільська": "Тернопіль",
    "харківська": "Харків", "херсонська": "Херсон", "хмельницька": "Хмельницький",
    "черкаська": "Черкаси", "чернівецька": "Чернівці", "чернігівська": "Чернігів"
}

currency_cache = {"data": None, "time": None}

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def get_currency():
    global currency_cache
    if currency_cache["data"] and currency_cache["time"] and (datetime.now() - currency_cache["time"]).seconds < 3600:
        return currency_cache["data"]
    try:
        r = requests.get("https://bank.gov.ua/NBU_Exchange/exchange_site?json", timeout=10)
        if r.status_code == 200:
            data = r.json()
            result = {}
            for item in data:
                code = item.get('cc')
                if code in ['USD', 'EUR', 'PLN', 'GBP', 'CHF', 'CZK']:
                    result[code] = {'rate': round(item.get('rate', 0), 2), 'txt': item.get('txt', code)}
            currency_cache["data"] = result
            currency_cache["time"] = datetime.now()
            return result
        return None
    except:
        return None

def get_weather_today(city):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city},UA&units=metric&lang=ua&appid={WEATHER_API_KEY}"
        r = requests.get(url)
        if r.status_code == 200:
            d = r.json()
            return f"📍 *{d['name']}*\n🌡️ {round(d['main']['temp'])}°C\n☁️ {d['weather'][0]['description'].capitalize()}\n💧 Вологість: {d['main']['humidity']}%\n💨 Вітер: {d['wind']['speed']} м/с"
        return None
    except:
        return None

def get_weather_week(city):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={city},UA&units=metric&lang=ua&appid={WEATHER_API_KEY}"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            daily = {}
            for item in data['list']:
                date = item['dt_txt'].split()[0]
                if date not in daily:
                    daily[date] = {'min': item['main']['temp_min'], 'max': item['main']['temp_max'], 'desc': item['weather'][0]['description']}
                else:
                    daily[date]['min'] = min(daily[date]['min'], item['main']['temp_min'])
                    daily[date]['max'] = max(daily[date]['max'], item['main']['temp_max'])
            result = f"📅 *Прогноз для {city}:*\n\n"
            for i, (date, info) in enumerate(list(daily.items())[:5]):
                day = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m')
                result += f"📌 *{day}*: {round(info['min'])}°C...{round(info['max'])}°C\n   ☁️ {info['desc'].capitalize()}\n\n"
            return result
        return None
    except:
        return None

def get_weather_smart(text):
    text = text.strip().lower()
    for region, city in REGIONS.items():
        if region in text:
            w = get_weather_today(city)
            if w:
                return w + f"\n\n📌 *{region.capitalize()} область* (центр — {city})"
            return f"📍 *{region.capitalize()} область*\nНе вдалося отримати погоду"
    w = get_weather_today(text)
    if w:
        return w
    return f"❌ Не знайшов '{text}'"

def ask_groq(q):
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": q}], "max_tokens": 600})
        a = r.json()["choices"][0]["message"]["content"]
        return re.sub(r'<think>.*?</think>', '', a, flags=re.DOTALL)
    except:
        return "Помилка"

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🤖 *Nelox AI* вітає!\n\n📌 *Команди:*\n• погода Київ\n• погода на тиждень Київ\n• /kurs\n• /coin\n• котра година\n• хто тебе створив", parse_mode='Markdown')

@bot.message_handler(commands=['kurs'])
def kurs(m):
    bot.send_chat_action(m.chat.id, 'typing')
    c = get_currency()
    if c:
        r = "💰 *Курс валют НБУ:*\n\n"
        for code, info in c.items():
            r += f"💵 *{code}* ({info['txt']}): {info['rate']} грн\n"
        bot.reply_to(m, r, parse_mode='Markdown')
    else:
        bot.reply_to(m, "❌ Не вдалося отримати курс")

@bot.message_handler(commands=['coin'])
def coin(m):
    bot.reply_to(m, f"🪙 *{random.choice(['Орел 🦅', 'Решка 💰'])}*", parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def handle(m):
    t = m.text.lower().strip()
    if "хто тебе створив" in t or "хто твій творець" in t:
        bot.reply_to(m, "👨‍💻 *Мене створив Діма Марущак!*", parse_mode='Markdown')
        return
    if "на тиждень" in t or "прогноз" in t:
        loc = re.sub(r'погода|на тиждень|прогноз|\s+', ' ', t).strip()
        if loc:
            r = get_weather_week(loc)
            bot.reply_to(m, r if r else f"❌ Не знайшов '{loc}'", parse_mode='Markdown')
        else:
            bot.reply_to(m, "📅 *Приклад:* погода на тиждень Київ", parse_mode='Markdown')
        return
    if "погода" in t:
        loc = re.sub(r'погода|\s+', ' ', t).strip()
        if loc:
            bot.reply_to(m, get_weather_smart(loc), parse_mode='Markdown')
        else:
            bot.reply_to(m, "🌤️ *Приклад:* погода Київ", parse_mode='Markdown')
        return
    if any(w in t for w in ["годин", "котра", "час"]):
        bot.reply_to(m, f"⏰ Зараз {get_time()}")
        return
    if t in ["привіт", "hi"]:
        bot.reply_to(m, "Привіт! Я Nelox AI. Мене створив Діма Марущак! 😊")
        return
    if "як тебе звати" in t or "твоє ім'я" in t:
        bot.reply_to(m, "Мене звуть *Nelox AI*! 🤖", parse_mode='Markdown')
        return
    bot.send_chat_action(m.chat.id, 'typing')
    bot.reply_to(m, ask_groq(m.text))

print("✅ Nelox AI запущено!")
bot.infinity_polling()
