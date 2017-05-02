from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import time
import json
import re


class MattressNextDayCoUkSpider(BaseSpider):
    name = 'mattressnextday.co.uk'
    allowed_domains = ['mattressnextday.co.uk']

    def __init__(self, *args, **kwargs):
        super(MattressNextDayCoUkSpider, self).__init__(*args, **kwargs)
 
    def start_requests(self):
        yield Request('http://www.mattressnextday.co.uk/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select(u'//ul[@class="megamenu"]/li/a/..'):
            for url in cat.select(u'.//a/@href').extract():
                if url == '#':
                    continue
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product_list,
                              meta={'category': cat.select(u'normalize-space(./a/text())').extract()[0]})

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        path = ''
        pattern = r"'([A-Za-z0-9_\./\\-]*)'"
        for line in hxs.extract().split('\n'):
            if 'path = ' in ' '.join(line.split()):
                text = ' '.join(line.split())
                path = re.search(pattern, text).group().replace("'", '')
        if path:
            category_id = hxs.select('//select[@name="sort_by"]/@id').extract()[0].replace('sort_by_','')
            product_list_url = ('http://www.mattressnextday.co.uk/index.php?route=api/' +
                               'category/getProducts&sort_by=price_low_to_high&'+
                               'category_id='+category_id+'&price_range=all&'+
                               'layout=grid&path='+path+'&per_page=1000&page=1')
            yield Request(product_list_url, callback=self.parse_product_list, meta=response.meta)
        
        for url in hxs.select('//div[@class="name"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_list = hxs.select(u'//div[@class="box"]/div/a/@href').extract()
        if product_list:
            for url in product_list:
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product, meta=response.meta)
            return

        #fill main product fields
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', response.meta.get('category'))
        img = hxs.select('//div[@class="image"]/img/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        brand = ''.join(hxs.select('//li[contains(text(), "Brand")]/text()').extract()).replace('Brand: ', '')
        product_loader.add_value('brand', brand)
        name = hxs.select('//div[@class="description"]/strong/text()').extract()[0]
        product = product_loader.load_item()

        #construct url for ajax request to grab all product options
        pid = hxs.select('//input[@name="product_id"]/@value').extract()
        if pid:
            for line in hxs.extract().split('\n'):
                if 'var isclearance' in line.lower() and 'true' in line.lower():
                    clearance = 'true'
                else:
                    clearance = 'false'
            url = 'http://www.mattressnextday.co.uk/?route=api/product/sizes&timestamp={}&productId={}&callback=jQuery110206226998819969816_1389291112656&storeId=0&isClearance={}&_=1389291112657'.format(int(time.time()), pid[0], clearance)
            yield Request(url, meta={'product': product}, callback=self.get_product_options)
        else:
            self.log('ERROR! Unable to parse product ID from url: {}'.format(response.url))
        
    def get_product_options(self, response):
        product = response.meta['product']
        try:
            data = json.loads(response.body.split('(')[1][:-1])
        except:
            data = json.loads(response.body.partition('(')[-1][:-1])

        name = data['details']['item_title']
        for size in data['sizes']:
            product['name'] = name + ' ' + size['size']
            product['identifier'] = str(size['id']) + '-' + str(size['size_id'])
            product['sku'] = size['sku']
            product['stock'] = size['stock']
            product['price'] = size['price']
            yield product
