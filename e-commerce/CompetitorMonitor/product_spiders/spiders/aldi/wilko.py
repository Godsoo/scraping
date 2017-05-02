import os
import re
import json
import urllib
from decimal import Decimal

from scrapy import Spider
from scrapy.http import Request
try:
    from scrapy.selector import Selector
except:
    from scrapy.selector import HtmlXPathSelector as Selector

from product_spiders.utils import extract_price

from scrapy.utils.url import add_or_replace_parameter, url_query_parameter


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class WilkoSpider(Spider):
    name = 'aldi-wilko.com'
    allowed_domains = ['wilko.com', 'fsm4.attraqt.com']
    start_urls = ['http://www.wilko.com/']

    user_agent = 'spd'

    search_terms = ['DYSON', 'NOTEBOOK', 'LAPTOP', 'WIRELESS ACTIVITY', 'PANINI', 'INVERTER GENERATOR', 'TV',
                    'HARD DRIVE', 'FRIDGES', 'SEWING MACHINE', 'MEMORY FOAM', 'DRYWALL SANDER', 'CIRCULAR SAW',
                    'BLENDER', 'CAR SEAT', 'COT', 'COOKER', 'LADDER', 'MICROWAVES', 'MOBILE', 'PHONE',
                    'LAWN MOWERS', 'PRUNER', 'SANDING', 'ROLLER', 'STAND MIXER']

    base_url = ('http://fsm4.attraqt.com/zones-js.aspx?version=16.5.3&siteId=80a8c829-e1d6-468e-b9f3-1d43e749feda'
                '&UID=27e48e8c-48a9-d4d8-57aa-284fcc6e4547&SID=3b3e0900-8c8a-fed9-bdba-e6853ce8d996'
                '&pageurl=&tracking=203-1035-9845'
                '&facetmode=data&mergehash=true&currency=GBP&config_categorytree=shop'
                '&config_category=shop&config_parentcategorytree=&config_parentcategory=undefined&config_language=en'
                '&config_region=restofworld&config_pdxttype=&config_pdxtcolour=&config_pdxtbrand=&config_pdxtsize='
                '&config_sys_price=&config_pdxtstarrating=&config_pdxtpromo=&config_accessoryskus='
                '&config_fsm_sid=3b3e0900-8c8a-fed9-bdba-e6853ce8d996&config_fsm_returnuser=1'
                '&config_fsm_currentvisit=11%2F10%2F2016&config_fsm_visitcount=8&config_fsm_lastvisit=10%2F10%2F2016')

    category_base_url = ('http://fsm4.attraqt.com/zones-js.aspx?version=2.23.2&siteId=80a8c829-e1d6-468e-b9f3-1d43e749feda'
                         '&UID=00717a5a-b291-a668-8d33-72965e152c82&SID=b05ef0cd-d07b-0229-c859-e5c54632099f'
                         '&pageurl=&zone0=category&tracking=203-1036-20495&facetmode=data&mergehash=true'
                         '&currency=GBP&config_categorytree=&config_category='
                         '&config_language=en&config_fsm_sid=b05ef0cd-d07b-0229-c859-e5c54632099f&config_fsm_returnuser=1'
                         '&config_fsm_currentvisit=10%2F06%2F2016&config_fsm_visitcount=2&config_fsm_lastvisit=09%2F06%2F2016')

    def start_requests(self):
        search_url = 'http://www.wilko.com/search?q=%s'
        for search_term in self.search_terms:
            operator = 'AND'
            if len(search_term.split()) > 1:
                operator = 'OR'
            search_term = search_term.replace(' ', '+')
            yield Request(search_url % search_term, meta={'operator': operator})

    def parse(self, response):
        url = add_or_replace_parameter(self.base_url, 'pageurl', response.url)
        url = add_or_replace_parameter(url, 'zone0', 'search')
        url = add_or_replace_parameter(url, 'searchoperator', response.meta['operator'])

        yield Request(url, meta={'url': response.url}, callback=self.parse_list)

    def parse_list(self, response):
        try:
            data = re.search('LM\.buildZone\((.*)\);', response.body).group(1)
        except AttributeError:
            data = re.search('LM\.redirect\((.*)\);', response.body).group(1)
            data = json.loads(data)
            yield Request(data['targetUrl'], callback=self.parse_category_redirect)
            return

        data = json.loads(data)

        sel = Selector(text=data['html'])

        pages = sel.xpath('//span[@class="pagnNumbers"]/a/@data-page').extract()
        for page in pages:
            page_url = response.meta['url'] + '#esp_pg=' + page
            url = add_or_replace_parameter(response.url, 'pageurl', page_url)
            yield Request(url, meta=response.meta, callback=self.parse_list)

        products = sel.xpath('//input[@name="invt"]/@value').extract()
        for prod_id in products:
            yield Request('http://www.wilko.com/invt/{}'.format(prod_id), callback=self.parse_product)

    def parse_category_redirect(self, response):
        category_tree = response.xpath('//input[@data-esp-category-tree]/@value').extract()
        if category_tree:
            category_tree = [c for c in category_tree[0].split('|') if c]
            category_tree = '/'.join(category_tree)

            url = add_or_replace_parameter(self.category_base_url, 'pageurl', response.url)
            url = add_or_replace_parameter(url, 'zone0', 'category')
            url = add_or_replace_parameter(url, 'config_categorytree', category_tree)
            url = add_or_replace_parameter(url, 'config_category', category_tree.split('/')[-1])

            yield Request(url, meta={'config_categorytree': category_tree, 'url': response.url},
                          callback=self.parse_category)

    def parse_category(self, response):
        data = re.search('LM\.buildZone\((.*)\);', response.body).group(1)
        data = json.loads(data)

        sel = Selector(text=data['html'])

        pages = sel.xpath('//span[@class="pagnNumbers"]/a/@data-page').extract()
        for page in pages:
            page_url = response.meta['url'] + '#esp_pg=' + page
            url = add_or_replace_parameter(response.url, 'pageurl', page_url)
            yield Request(url, meta=response.meta, callback=self.parse_category)

        products = sel.xpath('//input[@name="invt"]/@value').extract()
        for prod_id in products:
            yield Request('http://www.wilko.com/invt/{}'.format(prod_id), callback=self.parse_product)

    def parse_product(self, response):
        name = response.xpath('//*[@itemprop="name"]/text()').extract()
        name = name[0].strip()
        price = response.xpath('//*[@itemprop="price"]/text()').extract()
        sku = response.xpath('//*[@itemprop="sku"]/@content').extract()
        categories = response.xpath('//a[@class="crumbtrail-anchor"]/text()').extract()
        image_url = response.xpath('//*[@property="og:image"]/@content').extract()
        image_url = image_url[0] if image_url else ''

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        loader.add_value('category', categories)
        loader.add_value('image_url', image_url)
        loader.add_value('url', response.url)
        loader.add_xpath('brand', '//*[@itemprop="brand"]/text()')
        out_of_stock = response.xpath('//div[@class="out-of-stock"]')
        only_in_store = response.xpath('//div[@id="ais"]/p[@class="unavailable-msg"]')
        if out_of_stock or only_in_store:
            loader.add_value('stock', 0)
        shipping_cost = response.xpath('//h3[contains(text(), "Home Delivery")]/span[@class="delPrice"]/text()').extract()
        if shipping_cost:
            loader.add_value('shipping_cost', extract_price(shipping_cost[0]))

        yield loader.load_item()
