from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
from fp.fp import FreeProxy
from pymongo import MongoClient
import time

MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_DB = "mail"
MONGO_COLLECTION = "mail_ru"

proxies = FreeProxy().get_proxy_list()
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                  " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36"
}

driver = webdriver.Chrome(executable_path='./chromedriver')


def dt_convert(date_str):
    today = datetime.now()
    tomorrow = datetime.now() - timedelta(1)
    date_str = date_str.replace('Сегодня', today.strftime('%d.%m.%Y'))
    date_str = date_str.replace('Вчера', tomorrow.strftime('%d.%m.%Y'))
    return date_str

"""link = 'https://mail.ru'"""
def collect_mail(link, login, pwd):
    driver.get(link)
    elem = driver.find_element_by_name('login')
    elem.send_keys(login)
    elem.send_keys(Keys.ENTER)
    driver.implicitly_wait(10)

    elem = driver.find_element_by_name('password')
    elem.send_keys(pwd)
    elem.send_keys(Keys.ENTER)
    driver.implicitly_wait(10)

    db = set()  # множество под ссылки
    container = driver.find_elements_by_xpath("//a[contains(@class, 'js-letter-list-item')]")
    while True:
        for el in container:
            db.add(el.get_attribute('href'))
        data_id = container[-1].get_attribute('data-id')  # сохраняем ид последнего элемента
        container[-1].send_keys(Keys.PAGE_DOWN)  # скролим
        time.sleep(0.3)
        container = driver.find_elements_by_xpath("//a[contains(@class, 'js-letter-list-item')]")
        if data_id == container[-1].get_attribute('data-id'):  # сравниваем ид
            break
    base = []  # список для БД
    for el in db:
        driver.get(el)
        letter = {'from': driver.find_element_by_class_name('letter-contact').text,
                'date': dt_convert(driver.find_element_by_class_name('letter__date').text),
                'href': el,
                'body': driver.find_element_by_class_name('letter-body').text}
        base.append(letter)
        driver.close()
    return base


def to_mongo(base):
    with MongoClient(MONGO_HOST, MONGO_PORT) as client:
        db = client[MONGO_DB]
        users = db[MONGO_COLLECTION]
        for item in base:
            filter_data = {"from": item['from']}
            update_data = {
                "$set": {
                    "date": item['date'],
                    "href": item['href'],
                    'body': item['body']
                }
            }
            users.update_one(filter_data, update_data, upsert=True)


base = collect_mail()
to_mongo(base)

