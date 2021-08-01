import requests
from datetime import datetime
from fp.fp import FreeProxy
from lxml.html import fromstring
from pymongo import MongoClient

MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_DB = "db_hh"
MONGO_COLLECTION = "news"


def date_format(date_str, src):  # src=1 mail, src=2 yandex
    RU_MONTH_VALUES = {
        '01': 'января',
        '02': 'февраля',
        '03': 'марта',
        '04': 'апреля',
        '05': 'мая',
        '06': 'июня',
        '07': 'июля',
        '08': 'августа',
        '09': 'сентября',
        '10': 'октября',
        '11': 'ноября',
        '12': 'декабря'
    }
    if src == 1:
        time = date_str.split(' ')[1][:-9]
        date = date_str.split(' ')[0].split('-')
        for k, v in RU_MONTH_VALUES.items():
            date[1] = date[1].replace(str(k), str(v))
        return f'{time}, {date[2]} {date[1]} {date[0]}'
    elif src == 2:
        d = datetime.now()
        date = d.strftime("%Y-%m-%d").split('-')
        for k, v in RU_MONTH_VALUES.items():
            date[1] = date[1].replace(str(k), str(v))
        return f', {date[2]} {date[1]} {date[0]}'


proxies = FreeProxy().get_proxy_list()
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                  " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36"
}
url = ['https://news.mail.ru/', 'https://lenta.ru/', 'https://yandex.ru/news/?utm_source=main_stripe_big/']

info_about_items = []


def mail_news(url, headers, proxies):
    response = requests.get(url[0], headers=headers, proxies={"http": proxies[0]})
    items_xpath = '//ul/li[contains(@class, "list__item")]/a'
    dom = fromstring(response.text)
    items = dom.xpath(items_xpath)
    for element in items:
        info = {}
        dtlink = element.xpath('@href')[0]
        res_dt = requests.get(dtlink, headers=headers, proxies={"http": proxies[0]})
        dtdom = fromstring(res_dt.text)
        dt = dtdom.xpath('//div//span[contains(@class, "note__text breadcrumbs__text js-ago")]/@datetime')[0]
        src = dtdom.xpath('//div//a[contains(@class, "link color_gray")]/span')[0].text
        info['title'] = element.xpath('text()')[0].replace('\xa0', ' ')
        info['link'] = dtlink
        info['date'] = date_format(dt.replace('T', ' '), 1)
        info['src'] = src
        info['scrap_from'] = 'news.mail'
        info_about_items.append(info)


def lenta_news(url, headers, proxies):
    response = requests.get(url[1], headers=headers, proxies={"http": proxies[0]})
    items_xpath = "//div/section[contains(@class, 'top7')]//div[contains(@class, 'item')]//a[count(time)=1]"
    dom = fromstring(response.text)
    items = dom.xpath(items_xpath)
    for element in items:
        info = {}
        info['title'] = element.xpath('text()')[0].replace('\xa0', ' ')
        link = element.xpath('@href')[0]
        if link.find('http') == -1:
            info['link'] = url[1] + link[1:]
        else:
            info['link'] = link
        info['date'] = element.xpath('time/@datetime')[0][1:]
        info['src'] = 'lenta.ru'
        info['scrap_from'] = 'lenta.ru'
        info_about_items.append(info)


def yandex_news(url, headers, proxies):
    response = requests.get(url[2], headers=headers, proxies={"http": proxies[0]})
    items_xpath = "//div[contains(@class, '8 news-top')]/div"
    dom = fromstring(response.text)
    items = dom.xpath(items_xpath)
    for element in items:
        info = {}
        info['title'] = element.xpath(".//h2[contains(@class,'title')]/text()")[0].replace('\xa0', ' ')
        info['link'] = element.xpath(".//a/@href")[0]
        info['date'] = element.xpath(".//span[contains(@class,'source__time')]//text()")[0] + date_format(None, 2)
        info['src'] = element.xpath(".//a[contains(@class,'source-link')]//text()")[0]
        info['scrap_from'] = "yandex.news"
        info_about_items.append(info)


def to_mongo(base):
    with MongoClient(MONGO_HOST, MONGO_PORT) as client:
        db = client[MONGO_DB]
        users = db[MONGO_COLLECTION]
        for item in base:
            filter_data = {"title": item['title']}
            update_data = {
                "$set": {
                    "title": item['title'],
                    "url": item['link'],
                    'date': item['date'],
                    'source': item['src'],
                    'scrap_from': item['scrap_from']
                }
            }
            users.update_one(filter_data, update_data, upsert=True)


mail_news(url, headers, proxies)
lenta_news(url, headers, proxies)
yandex_news(url, headers, proxies)
to_mongo(info_about_items)

for item in info_about_items:
    print(item)
