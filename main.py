import requests
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from io import BytesIO
from PIL import Image
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
import math

YANDEX_API_KEY = '8013b162-6b42-4997-9691-77b7074026e0'
BOT_TOKEN = '7253763825:AAHLEW4kCm7b-eOTcRwgtKSNpcqiVABfaDA'

user_address = None
city = None


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        brand TEXT NOT NULL,
        model TEXT NOT NULL,
        city TEXT NOT NULL,
        found_address TEXT,
        search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()


init_db()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_kb = ReplyKeyboardMarkup(keyboard=[[
    KeyboardButton(text="Найти"),
    KeyboardButton(text="Статистика")], [KeyboardButton(text="Очистить данные")], [KeyboardButton(text="Адрес")]],
    resize_keyboard=True)


class Form(StatesGroup):
    brand = State()
    model = State()
    city = State()
    find = State()
    out = State()
    waiting_for_address = State()


# сохранение информации пользователя
def save_user_search(user_id, username, first_name, last_name, brand, model, city, found_address=None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO user_searches (user_id, username, first_name, last_name, brand, model, city, found_address)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, brand, model, city, found_address))

    conn.commit()
    conn.close()


# поиск информации пользователя
def get_user_searches(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT brand, model, city, found_address, search_date 
    FROM user_searches 
    WHERE username = ?
    ORDER BY search_date DESC
    ''', (username,))

    results = cursor.fetchall()
    conn.close()
    return results


def clear_user_data(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
    DELETE FROM user_searches 
    WHERE user_id = ?
    ''', (user_id,))

    deleted_rows = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_rows


def get_coords(city, address):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": f"{address} в {city}",
        "format": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Извлечение координат
    feature = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    longitude, latitude = feature["Point"]["pos"].split()

    return {"широта": float(latitude), "долгота": float(longitude)}



def find_auto_services(brand, model, city):
    # Ввод данных через консоль



    search_text = f"Автосервис {brand} {model} в {city}"

    # Запрос к API Яндекс.Карт
    geocoder_url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": search_text,
        "format": "json",
        "results": 25,
        "lang": "ru_RU"
    }

    response = requests.get(geocoder_url, params=params)
    data = response.json()

    features = data["response"]["GeoObjectCollection"]["featureMember"]
    if not features:
        return {}

    # Формируем словарь с результатами
    results = {}
    for i, feature in enumerate(features, 1):
        geo_object = feature["GeoObject"]
        address = geo_object["metaDataProperty"]["GeocoderMetaData"]["text"]
        longitude, latitude = geo_object["Point"]["pos"].split()

        results[f"Автосервис {i}"] = {
            "адрес": address,
            "координаты": {
                "широта": latitude,
                "долгота": longitude
            }
        }

    return results


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Вычисляет расстояние между двумя точками
    """
    R = 6371

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def sort_services_by_distance(services, target_point):
    """
    Сортирует автосервисы по расстоянию до точки
    """
    target_lat = target_point['широта']
    target_lon = target_point['долгота']

    for name, service in services.items():
        try:
            service_lat = float(service['координаты']['широта'])
            service_lon = float(service['координаты']['долгота'])
            distance = calculate_distance(target_lat, target_lon, service_lat, service_lon)
            service['расстояние_км'] = round(distance, 2)
        except (KeyError, ValueError):
            service['расстояние_км'] = float('inf')

    sorted_services = dict(sorted(
        services.items(),
        key=lambda item: item[1]['расстояние_км']
    ))

    return sorted_services


async def send_map_image(message: Message, coordinates: tuple, zoom=15):
    map_params = {
        "ll": f"{coordinates[0]},{coordinates[1]}",
        "l": "map",
        "z": str(zoom),
        "size": "650,450",
        "pt": f"{coordinates[0]},{coordinates[1]},pm2rdm"  # Добавляем метку
    }

    map_url = "https://static-maps.yandex.ru/1.x/"
    response = requests.get(map_url, params=map_params)

    if response.status_code == 200:
        img_bytes = BytesIO()
        img = Image.open(BytesIO(response.content))
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        await message.answer_photo(
            types.BufferedInputFile(img_bytes.read(), filename="map.png"),
            caption="Местоположение автосервиса"
        )
    else:
        await message.answer("Не удалось загрузить карту")



@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Я помогу найти автосервис для вашего автомобиля.", reply_markup=start_kb)


@dp.message(or_f(Command("brand"), (F.text.lower() == "найти")))
async def find(message: Message, state: FSMContext):
    await message.answer(
        "Введите марку автомобиля (например, Toyota):")
    await state.set_state(Form.model)


@dp.message(Form.model)
async def process_brand(message: Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await message.answer("Теперь введите модель автомобиля (например, Camry):")
    await state.set_state(Form.city)


@dp.message(Form.city)
async def process_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Введите город, где искать автосервис (например, Москва):")
    await state.set_state(Form.out)


@dp.message(Form.out)
async def process_city(message: Message, state: FSMContext):
    global city, user_address
    await state.update_data(city=message.text)
    city = message.text

    user_data = await state.get_data()

    brand = user_data['brand']
    model = user_data['model']
    city = user_data['city']

    search_text = f"Автосервис {brand} {model} в {city}"

    auto = find_auto_services(brand, model, city)
    user_coords = get_coords(city, user_address)
    sorted_list = sort_services_by_distance(auto, user_coords)

    res = list(sorted_list.items())[0]



    address = None
    coordinates = None
    for name, info in dict([res]).items():
        address = info['адрес']
        coordinates = (info['координаты']['долгота'], info['координаты']['широта'])

    await message.answer(f"Найден адрес: "
                         f"{address}")

    await send_map_image(message, coordinates)

    save_user_search(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        brand=brand,
        model=model,
        city=city,
        found_address=address
    )

    await state.clear()


@dp.message(or_f(Command("static"), (F.text.lower() == "статистика")))
async def show_statistics(message: Message):
    username = message.from_user.username
    if not username:
        await message.answer("У вас не установлен username в Telegram. Невозможно показать статистику.")
        return

    searches = get_user_searches(username)

    if not searches:
        await message.answer("У вас нет сохранённых запросов.")
        return

    response = "📊 Ваши последние запросы:\n\n"
    for i, search in enumerate(searches, 1):
        brand, model, city, address, date = search
        response += (
            f"🔹 Запрос #{i}\n"
            f"📅 Дата: {date}\n"
            f"🚗 Авто: {brand} {model}\n"
            f"🏙️ Город: {city}\n"
        )
        if address:
            response += f"📍 Найденный адрес: {address}\n"
        else:
            response += "📍 Адрес не найден\n"
        response += "\n"

    await message.answer(response)


@dp.message(or_f(Command("clear"), (F.text.lower() == "очистить данные")))
async def clear_data(message: Message):
    user_id = message.from_user.id
    deleted_rows = clear_user_data(user_id)

    if deleted_rows > 0:
        await message.answer(f"✅ Все ваши данные ({deleted_rows} записей) были удалены из базы.")
    else:
        await message.answer("ℹ️ У вас нет данных для удаления.")


@dp.message(or_f(Command("address"), (F.text.lower() == "адрес")))
async def handle_address(message: types.Message, state: FSMContext):
    global user_address

    if user_address:
        await message.answer(f"Текущий сохранённый адрес: {user_address}")
        return

    # Если адреса нет - запрашиваем его
    await message.answer("Пожалуйста, введите ваш адрес:")
    await state.set_state(Form.waiting_for_address)


@dp.message(Form.waiting_for_address)
async def save_address(message: types.Message, state: FSMContext):
    global user_address
    user_address = message.text
    await message.answer(f"Адрес сохранён: {user_address}")
    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
