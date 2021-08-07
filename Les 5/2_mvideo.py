# -*- coding: cp1251 -*-

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
from fp.fp import FreeProxy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from pprint import pprint
import ast
from pymongo import MongoClient
import time

MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_DB = "mvideo"
MONGO_COLLECTION = "new_items"

proxies = FreeProxy().get_proxy_list()
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                  " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36"
}

driver = webdriver.Chrome(executable_path='./chromedriver')


def collect_mail():
    driver.get('https://www.mvideo.ru/')
    xpath_next = "//*[contains(text(), 'Новинки')]//..//..//..//div[contains(@class,'gallery-content accessories-new " \
                 "')]//a[@class='next-btn c-btn c-btn_scroll-horizontal c-btn_icon i-icon-fl-arrow-right'] "
    xpath_new_items = "//*[contains(text(), 'Новинки')]//..//..//..//div[contains(@class,'gallery-content " \
                      "accessories-new ')]//li//a[@class='fl-product-tile-picture fl-product-tile-picture__link'] "

    next = driver.find_elements_by_xpath(xpath_next)
    while len(next) == 0:  # ищем новинки
        driver.find_element_by_xpath('//body').send_keys(Keys.PAGE_DOWN)
        driver.implicitly_wait(10)
        next = driver.find_elements_by_xpath(xpath_next)

    next_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_next)))

    while len(next) != 0:  # кликаем карусель
        driver.implicitly_wait(10)
        next_button.click()
        next = driver.find_elements_by_xpath(xpath_next)
        time.sleep(1)

    #  собираем информацию о новинках в контейнер
    elem = driver.find_elements_by_xpath(xpath_new_items)
    new_items = []
    for items in elem:
        new_items.append(ast.literal_eval(items.get_attribute('data-product-info').replace('\t\t\t\t\t', '').
                                          replace('\n', '')))
    return new_items


def to_mongo(base):
    with MongoClient(MONGO_HOST, MONGO_PORT) as client:
        db = client[MONGO_DB]
        users = db[MONGO_COLLECTION]
        for item in base:
            filter_data = {"productId": item['productId']}
            update_data = {
                "$set": {
                    "productId": item['productId'],
                    "Category": item['productCategoryName'],
                    "Name": item['productName'],
                    "Price": item['productPriceLocal'],
                    "Vendor": item['productVendorName']
                }
            }
            users.update_one(filter_data, update_data, upsert=True)


to_mongo(collect_mail())
