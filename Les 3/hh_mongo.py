import pickle
import time
from bs4 import BeautifulSoup as bs
from urllib.parse import quote_plus
import requests
import re
from pprint import pprint
from pymongo import MongoClient

MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_DB = "db_hh"
MONGO_COLLECTION = "vacansy"


def get(url, headers, proxies):
    r = requests.get(
        url,
        headers=headers,
        proxies=proxies
    )
    return r


def create_soup(r):
    return bs(r.text, 'html.parser')


def save_pickle(o, path):
    with open(path, 'wb') as f:
        pickle.dump(o, f)


def load_pickle(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


# min/max/currency separation
def sal_parse(sal_str):
    sal_dct = dict()
    val = re.split(' – | ', sal_str.replace('\u202f', ''))
    if val == ['None']:
        sal_dct = {'min': 'None', 'max': 'None', 'cur': 'None'}
    if len(val) == 3 and val[0] == 'от' and val[2] == 'руб.':
        sal_dct = {'min': int(val[1]), 'max': 'None', 'cur': 'руб.'}
    if len(val) == 3 and val[0] == 'от' and val[2] == 'USD':
        sal_dct = {'min': int(val[1]), 'max': 'None', 'cur': 'USD'}
    if len(val) == 3 and val[0] == 'от' and val[2] == 'EUR':
        sal_dct = {'min': int(val[1]), 'max': 'None', 'cur': 'EUR'}
    if len(val) == 3 and val[0] == 'до' and val[2] == 'USD':
        sal_dct = {'min': 'None', 'max': int(val[1]), 'cur': 'USD'}
    if len(val) == 3 and val[0] == 'до' and val[2] == 'руб.':
        sal_dct = {'min': 'None', 'max': int(val[1]), 'cur': 'руб.'}
    if len(val) == 3 and val[0] == 'до' and val[2] == 'EUR':
        sal_dct = {'min': 'None', 'max': int(val[1]), 'cur': 'EUR'}
    if len(val) == 3 and val[0] != 'до' and val[0] != 'от' \
            and val[1] != 'до' and val[1] != 'от' and val[2] == 'руб.':
        sal_dct = {'min': int(val[0]), 'max': int(val[1]), 'cur': 'руб.'}
    if len(val) == 3 and val[0] != 'до' and val[0] != 'от' \
            and val[1] != 'до' and val[1] != 'от' and val[2] == 'USD':
        sal_dct = {'min': int(val[0]), 'max': int(val[1]), 'cur': 'USD'}
    if len(val) == 3 and val[0] != 'до' and val[0] != 'от' \
            and val[1] != 'до' and val[1] != 'от' and val[2] == 'EUR':
        sal_dct = {'min': int(val[0]), 'max': int(val[1]), 'cur': 'EUR'}
    return sal_dct


def page_cnt(url, headers, proxies, max_page):
    r = get(url, headers, proxies)
    page_limit = create_soup(r).find_all("a",
                                         attrs={"class": "bloko-button", "rel": "nofollow", "data-qa": "pager-page"})
    page_limit = int(str(page_limit).split('<span>')[-1].split('<')[0])
    if page_limit < max_page:
        print('Error. Page quantity > Max page')
        return 'ERR'
    else:
        return page_limit


def url(vac_name, page):
    return f"https://spb.hh.ru/search/vacancy?st=searchVacancy&text={vac_name}&area=2&salary=&currency_code=RUR&\
        experience=doesNotMatter&order_by=relevance&search_period=0&items_on_page=20&no_magic=true&\
        L_save_area=true&page={page}"


def scrap(vac_name, max_page):
    base = []
    if page_cnt(url(vac_name, 0), headers, proxies, max_page) == 'ERR':
        return 'ERR'
    for page in range(0, max_page):
        r = get(url(vac_name, page), headers, proxies)
        soup = create_soup(r).find_all(attrs={"class": "vacancy-serp-item"})
        # save_pickle(r, path)
        # r = load_pickle(path)
        for item in soup:
            row = {'name': item.find(attrs={"data-qa": "vacancy-serp__vacancy-title"}).text,
                   'url': item.find('a', attrs={'class': 'bloko-link'}).attrs['href']}
            try:
                row['sal'] = item.select_one('div.vacancy-serp-item__sidebar').select_one('span').text
            except AttributeError:
                row['sal'] = 'None'
                pass
            row['sal'] = sal_parse(row['sal'])
            row['source'] = 'hh.ru'
            base.append(row)
        time.sleep(2)
    return base


def to_mongo(base):
    with MongoClient(MONGO_HOST, MONGO_PORT) as client:
        db = client[MONGO_DB]
        users = db[MONGO_COLLECTION]
        for item in base:
            filter_data = {"url": item['url']}
            update_data = {
                "$set": {
                    "name": item['name'],
                    "url": item['url'],
                    'sal': item['sal'],
                    'source': item['source']
                }
            }
            users.update_many(filter_data, update_data, upsert=True)


mode = int(input('Type mode:\n1- select\n2- update DB\n'))

if mode == 2:
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"}
    proxies = {'http': 'http://192.99.151.5:9300'}
    vname = input('Enter vacancy title: ')
    vac_name = quote_plus(vname)
    print(f'Total pages: {page_cnt(url(vac_name, 0), headers, proxies, 0)}')
    max_page = int(input('Page quantity: '))

    base = scrap(vac_name, max_page)
    if base != 'ERR':
        to_mongo(base)
elif mode == 1:
    try:
        inp_sal = int(input('Type salary to find: '))
        with MongoClient(MONGO_HOST, MONGO_PORT) as client:
            db = client[MONGO_DB]
            users = db[MONGO_COLLECTION]
            cursor = users.find({
                '$or': [{'sal.min': {'$gt': inp_sal}},
                        {'sal.max': {'$gt': inp_sal}}]
            })
            for doc in cursor:
                pprint(doc)
    except:
        pprint('Incorrect salary!')
й