import requests

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

print(name)
print(address)