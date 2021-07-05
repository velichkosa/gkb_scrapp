import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get('OW_KEY', None)


def cur_weather_data(city=input('Set city: ')):
    r = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric')
    print(f'Current temp in {city}: {round(r.json()["main"]["temp"], 1)}\u00b0C \n'
          f'Min temp: {round(r.json()["main"]["temp_min"], 1)}\u00b0C \n'
          f'Max temp: {round(r.json()["main"]["temp_max"], 1)}\u00b0C')


if __name__ == "__main__":
    cur_weather_data()
