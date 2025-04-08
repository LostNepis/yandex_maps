import requests
from PIL import Image
from io import BytesIO

API_KEY = 'fd68f2be-2c3a-42c3-ab7d-190007a9515c'
SEARCH_URL = 'https://search-maps.yandex.ru/v1/'
STATIC_MAP_URL = 'https://static-maps.yandex.ru/1.x/'

car_name = input().strip()
city = input().strip()

search_text = f"Автосервис {car_name} в {city}"

search_request = f'{SEARCH_URL}?apikey={API_KEY}&text={search_text}&lang=ru_RU&type=biz&results=1'
response = requests.get(search_request)

json_response = response.json()


feature = json_response["features"][0]
company = feature["properties"]["CompanyMetaData"]
name = company.get("name", "Без названия")
address = company.get("address", "Адрес не указан")
coords = feature["geometry"]["coordinates"]

print(name)
print(address)

map_params = {
        "ll": f"{coords[0]},{coords[1]}",
        "size": "450,450",
        "z": "16",
        "l": "map",
        "pt": f"{coords[0]},{coords[1]},pm2rdl"
    }
map_response = requests.get(STATIC_MAP_URL, params=map_params)

if map_response:
    image = Image.open(BytesIO(map_response.content))
    image.show()
else:
    print("Не удалось получить карту.")