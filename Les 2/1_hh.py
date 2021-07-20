import pickle
import time
from bs4 import BeautifulSoup as bs
from urllib.parse import quote_plus
import requests
import re
import pandas as pd
import csv


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
        sal_dct = {'min': val[1], 'max': 'None', 'cur': 'руб.'}
    if len(val) == 3 and val[0] == 'от' and val[2] == 'USD':
        sal_dct = {'min': val[1], 'max': 'None', 'cur': 'USD'}
    if len(val) == 3 and val[0] == 'от' and val[2] == 'EUR':
        sal_dct = {'min': val[1], 'max': 'None', 'cur': 'EUR'}
    if len(val) == 3 and val[0] == 'до' and val[2] == 'USD':
        sal_dct = {'min': 'None', 'max': val[1], 'cur': 'USD'}
    if len(val) == 3 and val[0] == 'до' and val[2] == 'руб.':
        sal_dct = {'min': 'None', 'max': val[1], 'cur': 'руб.'}
    if len(val) == 3 and val[0] == 'до' and val[2] == 'EUR':
        sal_dct = {'min': 'None', 'max': val[1], 'cur': 'EUR'}
    if len(val) == 3 and val[0] != 'до' and val[0] != 'от' \
            and val[1] != 'до' and val[1] != 'от' and val[2] == 'руб.':
        sal_dct = {'min': val[0], 'max': val[1], 'cur': 'руб.'}
    if len(val) == 3 and val[0] != 'до' and val[0] != 'от' \
            and val[1] != 'до' and val[1] != 'от' and val[2] == 'USD':
        sal_dct = {'min': val[0], 'max': val[1], 'cur': 'USD'}
    if len(val) == 3 and val[0] != 'до' and val[0] != 'от' \
            and val[1] != 'до' and val[1] != 'от' and val[2] == 'EUR':
        sal_dct = {'min': val[0], 'max': val[1], 'cur': 'EUR'}
    return sal_dct


def page_cnt(url, headers, proxies):
    r = get(url, headers, proxies)
    page_limit = create_soup(r).find_all("a",
                                         attrs={"class": "bloko-button", "rel": "nofollow", "data-qa": "pager-page"})
    if int(str(page_limit).split('<span>')[-1].split('<')[0]) < max_page:
        print('Error. Page quantity > Max page')
        return 'ERR'


def url(vac_name, page):
    return f"https://spb.hh.ru/search/vacancy?st=searchVacancy&text={vac_name}&area=2&salary=&currency_code=RUR&\
        experience=doesNotMatter&order_by=relevance&search_period=0&items_on_page=20&no_magic=true&\
        L_save_area=true&page={page}"


def scrap(vac_name, max_page):
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"}
    proxies = {'http': 'http://192.99.151.5:9300'}
    base = []
    if page_cnt(url(vac_name, 0), headers, proxies) == 'ERR':
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


def to_csv(base):
    with open('hh.csv', "w", newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(base[0].keys())
        for item in base:
            writer.writerow(item.values())


vname = input('Enter vacancy title: ')
vac_name = quote_plus(vname)
max_page = int(input('Page quantity: '))

base = scrap(vac_name, max_page)
if base != 'ERR':
    to_csv(base)
    hh_df = pd.read_csv('hh.csv', encoding='utf8')
    print(hh_df)
