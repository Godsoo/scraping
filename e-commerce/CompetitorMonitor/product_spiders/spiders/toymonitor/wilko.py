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


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class WilkoSpider(Spider):
    name = 'toymonitor-wilko.com'
    allowed_domains = ['wilko.com', 'fsm4.attraqt.com']
    start_urls = ['http://www.wilko.com/toys+bikes/icat/toysandleisure']

    user_agent = 'spd'

    def parse(self, response):
        categories = response.xpath('//ul[@id="categoryNavigation"]/li/ul/li/a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        category_tree = response.xpath('//input[@data-esp-category-tree]/@value').extract()
        if category_tree:
            category_tree = [c for c in category_tree[0].split('|') if c]
            category_tree = '/'.join(category_tree)
            url = ('http://fsm4.attraqt.com/zones-js.aspx?version=16.5.3&siteId=80a8c829-e1d6-468e-b9f3-1d43e749feda'
                   '&UID=27e48e8c-48a9-d4d8-57aa-284fcc6e4547&SID=fc886a2a-06e3-490a-2c88-0a2aab701962'
                   '&pageurl={page_url}&zone0=category&facetmode=html&mergehash=false'
                   '&currency=GBP&config_categorytree={config_categorytree}&config_category={config_category}'
                   '&config_language=en&config_region=restofworld&config_pdxttype=&config_pdxtcolour=&config_pdxtbrand='
                   '&config_pdxtsize=&config_sys_price=&config_pdxtstarrating=&config_pdxtpromo=&config_accessoryskus='
                   '&config_fsm_sid=fc886a2a-06e3-490a-2c88-0a2aab701962&config_fsm_returnuser=0'
                   '&config_fsm_currentvisit=03%2F10%2F2016&config_fsm_visitcount=1')
            yield Request(url.format(page_url=urllib.quote_plus(response.url),
                                     config_categorytree=urllib.quote_plus(category_tree),
                                     config_category=category_tree.split('/')[-1]),
                          meta={'config_categorytree': category_tree,
                                'url': response.url},
                          callback=self.parse_list)

    def parse_list(self, response):
        data = re.search('LM\.buildZone\((.*)\);', response.body).group(1)
        data = json.loads(data)

        sel = Selector(text=data['html'])

        pages = sel.xpath('//span[@class="pagnNumbers"]/a/@data-page').extract()
        url = ('http://fsm4.attraqt.com/zones-js.aspx?version=2.23.2&siteId=80a8c829-e1d6-468e-b9f3-1d43e749feda'
               '&UID=00717a5a-b291-a668-8d33-72965e152c82&SID=b05ef0cd-d07b-0229-c859-e5c54632099f'
               '&pageurl={page_url}%23esp_pg%3D{pagenum}&zone0=category&tracking=203-1036-20495&facetmode=data&mergehash=true'
               '&currency=GBP&config_categorytree={config_categorytree}&config_category={config_category}'
               '&config_language=en&config_fsm_sid=b05ef0cd-d07b-0229-c859-e5c54632099f&config_fsm_returnuser=1'
               '&config_fsm_currentvisit=10%2F06%2F2016&config_fsm_visitcount=2&config_fsm_lastvisit=09%2F06%2F2016')
        for page in pages:
            yield Request(url.format(page_url=urllib.quote_plus(response.meta['url']),
                                     config_categorytree=urllib.quote_plus(response.meta['config_categorytree']),
                                     config_category=response.meta['config_categorytree'].split('/')[-1],
                                     pagenum=page),
                          meta=response.meta,
                          callback=self.parse_list)

        products = sel.xpath('//input[@name="invt"]/@value').extract()
        for prod_id in products:
            yield Request('http://www.wilko.com/invt/{}'.format(prod_id), callback=self.parse_product)

    def parse_product(self, response):
        name = response.xpath('//h1[@class="prod-name"]/text()').extract()
        name = name[0].strip()
        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        sku = response.xpath('//meta[@itemprop="sku"]/@content').extract()
        categories = response.xpath('//a[@class="crumbtrail-anchor"]/text()').extract()
        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        image_url = image_url[0] if image_url else ''

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        loader.add_value('category', categories)
        loader.add_value('image_url', image_url)
        loader.add_value('url', response.url)
        loader.add_xpath('brand', '//div[@itemprop="brand"]/text()')
        out_of_stock = response.xpath('//div[@class="out-of-stock"]')
        only_in_store = response.xpath('//div[@id="ais"]/p[@class="unavailable-msg"]')
        if out_of_stock or only_in_store:
            loader.add_value('stock', 0)
        loader.add_value('shipping_cost', Decimal('4.00'))

        yield loader.load_item()
