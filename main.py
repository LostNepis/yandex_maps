import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from io import BytesIO
from PIL import Image

YANDEX_API_KEY = '8013b162-6b42-4997-9691-77b7074026e0'
BOT_TOKEN = '7253763825:AAHLEW4kCm7b-eOTcRwgtKSNpcqiVABfaDA'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class Form(StatesGroup):
    brand = State()
    model = State()
    city = State()


@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Я помогу найти автосервис для вашего автомобиля.\nВведите марку автомобиля (например, Toyota):")
    await state.set_state(Form.brand)


@dp.message(Form.brand)
async def process_brand(message: Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await message.answer("Теперь введите модель автомобиля (например, Camry):")
    await state.set_state(Form.model)


@dp.message(Form.model)
async def process_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Введите город, где искать автосервис (например, Москва):")
    await state.set_state(Form.city)


@dp.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    user_data = await state.get_data()

    brand = user_data['brand']
    model = user_data['model']
    city = user_data['city']

    search_text = f"Автосервис {brand} {model} в {city}"

    try:
        geocoder_url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            "apikey": YANDEX_API_KEY,
            "geocode": search_text,
            "format": "json",
            "results": 1,
            "lang": "ru_RU"
        }

        response = requests.get(geocoder_url, params=params)
        data = response.json()

        features = data["response"]["GeoObjectCollection"]["featureMember"]
        if not features:
            await message.answer("Ничего не найдено по вашему запросу.")
            await state.clear()
            return

        geo_object = features[0]["GeoObject"]
        coords = geo_object["Point"]["pos"]
        address = geo_object["metaDataProperty"]["GeocoderMetaData"]["text"]
        longitude, latitude = coords.split()

        # Получение карты
        map_url = "https://static-maps.yandex.ru/1.x/"
        map_params = {
            "ll": f"{longitude},{latitude}",
            "spn": "0.005,0.005",
            "l": "map",
            "pt": f"{longitude},{latitude},pm2rdm"
        }

        map_response = requests.get(map_url, params=map_params)

        await message.answer(f"🔍 Найден автосервис:\n📍 Адрес: {address}")

        img_bytes = BytesIO()
        img = Image.open(BytesIO(map_response.content))
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        await message.answer_photo(types.BufferedInputFile(img_bytes.read(), filename="map.png"))

    except Exception as e:
        raise (f"⚠️ Произошла ошибка: {str(e)}")

    await state.clear()


@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Поиск отменён.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())