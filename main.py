import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import re, os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

TOKEN = os.getenv('TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
COLLECTION_NAME = os.getenv('COLLECTION_NAME')


client = MongoClient(MONGO_URI)
db = client.get_database()
collection = db[COLLECTION_NAME]

bot = telebot.TeleBot(TOKEN)
search_criteria = {}
user_listings = {}

options = {
    "Город": "🌆 Город",
    "Тип дома": "🏠 Тип дома",
    "Жилой комплекс": "🏢 Жилой комплекс",
    "Год постройки": "📅 Год постройки",
    "Этаж": "📶 Этаж",
    "Площадь": "📏 Площадь",
    "Высота потолков": "📐 Высота потолков",
    "addressTitle": "📍 Адрес",
    "price": "💰 Цена",
    "rooms": "🚪 Количество комнат"
}

def generate_keyboard():
    markup = InlineKeyboardMarkup()
    for key, value in options.items():
        markup.add(InlineKeyboardButton(value, callback_data=f"filter_{key}"))
    markup.add(InlineKeyboardButton("🔍 Поиск", callback_data="search"))
    markup.add(InlineKeyboardButton("➕ Добавить объявление", callback_data="add_listing"))
    markup.add(InlineKeyboardButton("🗑 Удалить объявление", callback_data="delete_listing"))
    markup.add(InlineKeyboardButton("📂 Мои объявления", callback_data="my_listings"))
    markup.add(InlineKeyboardButton("🗑 Очистить параметры", callback_data="clear_filters"))
    return markup

def format_filters():
    if not search_criteria:
        return "Параметры не выбраны."
    return "\n".join([f"{options[key]}: {value}" for key, value in search_criteria.items()])

@bot.message_handler(commands=['start'])
def start(message):
    global search_criteria
    search_criteria = {}
    bot.send_message(message.chat.id, "Выберите параметры поиска:\n" + format_filters(), reply_markup=generate_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("filter_"))
def filter_selection(call):
    param = call.data.split("filter_")[1]
    bot.send_message(call.message.chat.id, f"Введите значение для '{options[param]}':")
    bot.register_next_step_handler(call.message, lambda msg: save_filter(param, msg))

def save_filter(param, message):
    global search_criteria
    search_criteria[param] = message.text.strip()
    bot.send_message(message.chat.id, f"Добавлен фильтр: {options[param]} = {message.text}\n" + format_filters(), reply_markup=generate_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "search")
def search(call):
    query = {}
    for key, value in search_criteria.items():
        if key == "rooms" or key == "price":
            try:
                query[f"data.{key}"] = int(value)
            except ValueError:
                bot.send_message(call.message.chat.id, f"Ошибка: {options[key]} должно быть числом.")
                return
        else:
            query[f"offer.{key}"] = {"$regex": value, "$options": "i"}
    results = collection.find(query).limit(5)
    print(query)
    send_results(call.message, results)

@bot.callback_query_handler(func=lambda call: call.data == "clear_filters")
def clear_filters(call):
    global search_criteria
    search_criteria = {}
    bot.send_message(call.message.chat.id, "Все параметры поиска очищены. Выберите заново:", reply_markup=generate_keyboard())

def escape_markdown(text):
    if not text:
        return ""
    escape_chars = r'_*[]()~>#+-=|{}.!'
    return "".join(f"\\{char}" if char in escape_chars else char for char in text)


def send_results(message, results):
    response = "*Результаты поиска:*\n"
    found = False
    for item in results:
        found = True
        title = escape_markdown(item["data"]["title"])
        price = escape_markdown(str(item["data"].get("price", "Цена не указана")))
        address = escape_markdown(item["data"].get("addressTitle", "Адрес не указан"))
        link = f"https://krisha.kz/a/show/{item['data']['id']}"
        response += f"🏠 *{title}*\n📍 _{address}_\n💰 *{price} KZT*\n🔗 [Перейти к объявлению]({link})\n\n"
    if not found:
        response = "Ничего не найдено. Попробуйте изменить параметры."
    bot.send_message(message.chat.id, response, parse_mode="MarkdownV2", disable_web_page_preview=True, reply_markup=generate_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "my_listings")
def my_listings(call):
    user_id = call.from_user.id
    listings = collection.find({"data.id": user_id})  
    send_results(call.message, listings)


@bot.callback_query_handler(func=lambda call: call.data == "delete_listing")
def delete_listing(call):
    user_id = call.from_user.id
    listings = list(collection.find({"data.id": user_id}))
    if not listings:
        bot.send_message(call.message.chat.id, "У вас нет объявлений.", reply_markup=generate_keyboard())
        return
    markup = InlineKeyboardMarkup()
    for item in listings:
        markup.add(InlineKeyboardButton(item["data"]["title"], callback_data=f"delete_{item['_id']}"))
    bot.send_message(call.message.chat.id, "Выберите объявление для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def confirm_delete(call):
    listing_id = call.data.split("delete_")[1]
    try:
        collection.delete_one({"_id": ObjectId(listing_id)})  
        bot.send_message(call.message.chat.id, "Объявление удалено.", reply_markup=generate_keyboard())
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Ошибка при удалении: {e}", reply_markup=generate_keyboard())


@bot.callback_query_handler(func=lambda call: call.data == "add_listing")
def add_listing(call):
    user_listings[call.from_user.id] = {
        "offer": {},
        "params": {},
        "data": {}
    }
    bot.send_message(call.message.chat.id, "Введите название объявления:")
    bot.register_next_step_handler(call.message, lambda msg: save_title(call.from_user.id, msg))

def save_title(user_id, message):
    user_listings[user_id]["data"]["title"] = message.text
    bot.send_message(message.chat.id, "Введите цену объявления:")
    bot.register_next_step_handler(message, lambda msg: save_price(user_id, msg))

def save_price(user_id, message):
    try:
        price = int(message.text)
        user_listings[user_id]["data"]["price"] = price
        user_listings[user_id]["data"]["hasPrice"] = True
        ask_next_param(user_id, message.chat.id)
    except ValueError:
        bot.send_message(message.chat.id, "Цена должна быть числом. Пожалуйста, введите цену снова:")
        bot.register_next_step_handler(message, lambda msg: save_price(user_id, msg))

def ask_next_param(user_id, chat_id):
    remaining_keys = [key for key in options.keys() if key not in user_listings[user_id]["offer"]]
    if remaining_keys:
        next_key = remaining_keys[0]
        bot.send_message(chat_id, f"Введите значение для '{options[next_key]}':")
        bot.register_next_step_handler_by_chat_id(chat_id, lambda msg: save_param(user_id, next_key, msg))
    else:
        save_listing_to_db(user_id, chat_id)

def save_param(user_id, key, message):
    user_listings[user_id]["offer"][key] = message.text
    if key == "rooms":
        try:
            rooms = int(message.text)
            user_listings[user_id]["data"]["rooms"] = rooms
        except ValueError:
            bot.send_message(message.chat.id, "Количество комнат должно быть числом. Пожалуйста, введите значение снова:")
            bot.register_next_step_handler(message, lambda msg: save_param(user_id, key, msg))
            return
    ask_next_param(user_id, message.chat.id)

def save_listing_to_db(user_id, chat_id):
    new_listing = user_listings[user_id]
    new_listing["data"]["id"] = user_id
    new_listing["data"]["ownerName"] = f"id{user_id}"
    collection.insert_one(new_listing)
    bot.send_message(chat_id, "Объявление успешно добавлено!", reply_markup=generate_keyboard())
    del user_listings[user_id]


if __name__ == "__main__":
    bot.polling(none_stop=True)