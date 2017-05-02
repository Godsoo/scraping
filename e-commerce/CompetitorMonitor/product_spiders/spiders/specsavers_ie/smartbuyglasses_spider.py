import urlparse
import os
import json
import re

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class SmartBuyGlassesSpider(BaseSpider):
    name = 'specsavers_ie-smartbuyglasses.ie'
    allowed_domains = ['smartbuyglasses.ie']
    start_urls = ['http://www.smartbuyglasses.ie/']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # categories and subcategories
        categories = response.xpath('//ul[@class="nav_menuN"]//a/@href').extract()
        for cat_href in categories:
            yield Request(urlparse.urljoin(get_base_url(response), cat_href))

        # products
        products = response.xpath('//div[contains(@class, "proCell")]/ul/a/@href').extract()
        for url in products:
            yield Request(url, callback=self.parse_product)

        next = response.xpath('//a[img[contains(@src, "arrow_right")]]/@href').extract()
        if not next:
            next = response.xpath('//a[i[contains(@class, "right")]]/@href').extract()

        if next:
            yield Request(next[0])

        brand_type = re.findall('brandType:"(.*)"', response.body)
        subcategory = re.findall('subCategory:"(.*)"', response.body)
        category = re.findall('categoryString:"(.*)"', response.body)
        current_page = response.xpath('//input[@id="current-page"]/@value').extract()
        if brand_type and current_page:
            formdata = {'brand_type': brand_type[0],
                        'category': category[0],
                        'p': current_page[0],
                        'subcategory': subcategory[0],
                        's': '0',
                        'tb': '0'}
            url = 'http://www.smartbuyglasses.ie/contact-lens/auto-filter-search'
            yield FormRequest(url, formdata=formdata, callback=self.parse_contact_lens, meta={'formdata': formdata})

        identifier = re.findall("prodId:\['(.*)'\]", response.body)
        if identifier:
            for item in self.parse_product(response):
                yield item

    def parse_contact_lens(self, response):
        data = json.loads(response.body)

        products = []
        
        for product_data in data['data']:
            if isinstance(product_data, list):
                 for product in product_data:
                     products.append(product)
            else:
                for id, product in product_data.iteritems():
                     products.append(product)

        for product in products:
            yield Request(product['webUrl'], callback=self.parse_product, meta={'shipping_cost': 3.99})

        formdata = response.meta['formdata']
        if int(formdata['p']) < data['pageCount']:
            url = 'http://www.smartbuyglasses.ie/contact-lens/auto-filter-search'
            formdata['p'] = str(int(formdata['p']) + 1)
            yield FormRequest(url, formdata=formdata, callback=self.parse_contact_lens, 
                              meta={'formdata': formdata})
        

    def parse_product(self, response):
	url = response.url
 
        products = response.xpath('//li[@class="similar_content_element"]/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)

        l = ProductLoader(item=Product(), response=response)

        try:
            name = response.xpath('//h1/text()').extract()[0].strip()
        except IndexError:
            retry = response.meta.get('retry', 0)
            if retry <= 3:
                yield Request(response.url, dont_filter=True, callback=self.parse_product, meta={'retry': retry + 1})
            else:
                log.msg('ERROR >>> Product without name: ' + response.url)
            return

        l.add_value('name', name)


        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        
        price = extract_price(price[0]) if price else '0'
        l.add_value('price', price)

        identifier = re.findall("prodId:\['(.*)'\]", response.body)[0]
        l.add_value('identifier', identifier)
        l.add_value('sku', identifier)
        brand = re.findall("pbrand:\['(.*)'\]", response.body)[0]
        l.add_value('brand', brand)
        categories = response.xpath('//div[@class="navigation"]//a/h2/text()').extract()
        if not categories:
            categories = response.xpath('//div[@class="local"]//a/text()').extract()[1:]
        l.add_value('category', categories)

        image_url = response.xpath('//img[@id="big_image"]/@src').extract()
        if not image_url:
            image_url = response.xpath('//img[@id="fancybox-cl-img"]/@src').extract()

        if image_url:
            l.add_value('image_url', urlparse.urljoin(get_base_url(response), image_url[0]))
        l.add_value('url', url)

        l.add_value('shipping_cost', response.meta.get('shipping_cost', 0))


        product = l.load_item()


        yield product
