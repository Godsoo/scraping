"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4958-e-bedding-%7C-wilko-%7C-new-site/details#
This spider is set to extract all items from the Bedding category.
"""
import re
import json
import urllib
from decimal import Decimal

from scrapy.http import Request
from scrapy.spider import BaseSpider
try:
    from scrapy.selector import Selector
except:
    from scrapy.selector import HtmlXPathSelector as Selector

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class EBeddingWilkoSpider(BaseSpider):
    name = 'ebedding-wilko.com'
    allowed_domains = ['wilko.com', 'fsm4.attraqt.com']
    start_urls = ['http://www.wilko.com/home-living/bedding/icat/sheetsandbedding']

    def parse(self, response):
        categories = response.xpath('//ul[@id="categoryNavigation"]/li/ul/li/a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        category_tree = response.xpath('//input[@data-esp-category-tree]/@value').extract()
        if category_tree:
            category_tree = [c for c in category_tree[0].split('|') if c]
            category_tree = '/'.join(category_tree)
            url = ('http://fsm4.attraqt.com/zones-js.aspx?version=2.23.2&siteId=80a8c829-e1d6-468e-b9f3-1d43e749feda'
                  '&UID=00717a5a-b291-a668-8d33-72965e152c82&SID=b05ef0cd-d07b-0229-c859-e5c54632099f'
                  '&pageurl={page_url}&zone0=category&tracking=203-1036-20495&facetmode=data&mergehash=true'
                  '&currency=GBP&config_categorytree={config_categorytree}&config_category={config_category}'
                  '&config_language=en&config_fsm_sid=b05ef0cd-d07b-0229-c859-e5c54632099f&config_fsm_returnuser=1'
                  '&config_fsm_currentvisit=10%2F06%2F2016&config_fsm_visitcount=2&config_fsm_lastvisit=09%2F06%2F2016')
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
        loader = ProductLoader(item=Product(), response=response)
        # name
        name = response.xpath('//h1[@class="prod-name"]/text()').extract()
        name = name[0].strip()
        loader.add_value('name', name)

        # price
        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        loader.add_value('price', price)

        # sku
        sku = response.xpath('//meta[@itemprop="sku"]/@content').extract()
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)

        # category
        categories = response.xpath('//a[@class="crumbtrail-anchor"]/text()')[1:].extract()
        for category in categories:
            loader.add_value('category', category)

        # product image
        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', image_url)
        # url
        loader.add_value('url', response.url)
        # brand
        loader.add_xpath('brand', '//div[@itemprop="brand"]/text()')
        # stock
        out_of_stock = response.xpath('//div[@class="out-of-stock"]')
        if out_of_stock:
            loader.add_value('stock', 0)
        # shipping cost
        loader.add_value('shipping_cost', Decimal('4.00'))

        yield loader.load_item()

