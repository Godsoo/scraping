# -*- coding: utf-8 -*-
from __future__ import with_statement

import json
import datetime
import math
from scrapy.spider import BaseSpider
from scrapy.http import FormRequest
from product_spiders.items import Product, ProductLoader


def date_plus_1_month(date_obj):
    month = date_obj.month
    year = date_obj.year
    if month == 12:
        new_year = year + 1
        new_month = 1
    else:
        new_year = year
        new_month = month + 1

    day = date_obj.day

    future = None
    while not future:
        try:
            future = datetime.date(new_year, new_month, day)
        except ValueError:
            day -= 1

    return future

cities = [
    "Akko, Israel",
    "Almog, West Bank and Gaza",
    "Arad, Israel",
    "Ashkelon, Israel",
    "Bat Yam, Israel",
    "Beersheba, Israel",
    "Be'er Ya'akov, Israel",
    "Bethlehem, West Bank and Gaza",
    "Caesarea, Israel",
    "Dor, Israel",
    "Eilat (and vicinity), Israel",
    "Ein Bokek, Israel",
    "Ein Gedi, Israel",
    "Ein Gev, Israel",
    "Ginosar, Israel",
    "Gonen, Israel",
    "Haifa, Israel",
    "Herzliya, Israel",
    "Jerusalem (and vicinity), Israel",
    "Kfar Blum, Israel",
    "Kfar Giladi, Israel",
    "Lavi, Israel",
    "Ma'alot - Tarshiha, Israel",
    "Maagan, Israel",
    "Ma'ale Hachamisha, Israel",
    "Mitzpe Ramon, Israel",
    "Nahsholim, Israel",
    "Nahariya, Israel",
    "Nazareth, Israel",
    "Netanya, Israel",
    "Neve Ativ, Israel",
    "Newe Ilan, Israel",
    "Neve Zohar, Israel",
    "Ramat Gan, Israel",
    "Ramot, Israel",
    "Rosh Pinna, Israel",
    "Hazor Haglilit, Israel",
    "Safed, Israel",
    "Shavei Zion, Israel",
    "Shefayim, Israel",
    "Shoresh, Israel",
    "Tel Aviv (and vicinity), Israel",
    "Tiberias, Israel",
    "Tzuba, Israel",
    "Yesod HaMa'ala, Israel"
]

nights = 3

date_format = '%m/%d/%Y'

class ExpediaComSpider(BaseSpider):
    name = "expedia.com"
    allowed_domains = ["expedia.com"]
    start_urls = (
        'http://www.expedia.com/Hotels',
        )

    # search_url = 'http://www.expedia.com//Hotel-Search'
    search_url = 'http://www.expedia.com/Hotel-Search?inpAjax=true'

    def parse(self, response):
        # calculate calendar values
        today = datetime.date.today()
        checkin_date = date_plus_1_month(today)
        checkout_date = checkin_date + datetime.timedelta(days=nights)

        for city in cities:
            params = {
                'destination': city,
                'startDate': checkin_date.strftime(date_format),
                'endDate': checkout_date.strftime(date_format),
                'adults': '2',
                'star': '0'
            }

            request = FormRequest(self.search_url, formdata=params, callback=self.parse_items)
            yield request

    def parse_items(self, response):
        # hxs = HtmlXPathSelector(response)

        # search_params = hxs.select("//script").re(u'\\\\"searchWizard\\\\":(.*?),[\s]*\\\\"searchWizardInitial\\\\"')
        # search_params = json.loads(search_params[0].replace(r'\"', r'"'))['d']

        result = json.loads(response.body)
        search_params = result['searchWizard']['d']

        region_id = search_params[0]
        destination = search_params[1]
        start_date = search_params[7]
        end_date = search_params[8]

        total_count = search_params[-2]

        offersPerPage = 50

        for page in range(0, int(math.ceil(float(total_count) / offersPerPage)) + 1):
            params = {
                'destination': destination,
                'startDate': start_date,
                'endDate': end_date,
                'adults': '2',
                'regionId': region_id,
                'total': str(total_count),
                'rfrrid': '-56907',
                'lodging': 'all',
                'sort': 'mostPopular',
                'page': str(page)
            }

            request = FormRequest(self.search_url, formdata=params, callback=self.parse_pages)
            yield request

        return

    def parse_pages(self, response):
        result = json.loads(response.body)

        items = []
        if 'retailHotelModelListFirst' in result:
            items += result['retailHotelModelListFirst']['d'][0]
        if 'retailHotelModelListLast' in result:
            items += result['retailHotelModelListLast']['d'][0]

        products = 0
        for item in items:
            item = item['d']

            name = item[0]['d'][5]
            price = item[1]['d'][4].replace(',', '')
            url = item[-5]
            if float(price):
                price = float(price) * nights
                l = ProductLoader(item=Product(), response=response)
                l.add_value('name', name.encode('ascii', 'replace'))
                l.add_value('identifier', name.encode('ascii', 'replace'))
                l.add_value('url', url)
                l.add_value('price', price)
                yield l.load_item()
                products += 1
