import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class IntertoysNlSpider(BaseSpider):
    name = 'intertoys.nl'
    allowed_domains = ['intertoys.nl']
    start_urls = ['http://www.intertoys.nl/lego']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for cat in hxs.select('//div[contains(@class, "TopCategory")]//ul/li/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        catalog_id = hxs.select('//input[@name="catalogId"]/@value').extract()[0]
        category_id = re.search(r"categoryId: '(.*)'}", response.body)
        if not category_id:
           return
        category_id = category_id.group(1)
        url = "http://www.intertoys.nl/CategoryNavigationResultsView?pageSize=999&manufacturer=LEGO&searchType=&catalogId=%s&categoryId=%s" % (catalog_id, category_id)
        yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        try:
            for product in hxs.select('//div[contains(@class, "product_name")]/a/@href').extract():
                yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)
        except:
            retry_count = response.meta.get('retry', 0)
            if retry_count < 5:
                yield Request(response.url, callback=self.parse_products, meta={'retry': retry_count + 1})
            
        
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        identifier = hxs.select('//tr[th[contains(text(), "Artikelnummer")]]/td/text()').extract()
        if not identifier:
            return
        loader.add_value('identifier', identifier[0])
        loader.add_value('url', response.url)
        name = hxs.select('//h1//text()').extract()[0].strip()
        loader.add_value('name', name)

        price = hxs.select('//meta[@itemprop="price"]').extract()


        loader.add_value('price', price[0])

        sku = re.search('(\d+)', loader.get_output_value('name'))
        if sku:
            loader.add_value('sku', sku.groups()[0])
        else:
            loader.add_value('sku', '')

        category = hxs.select('//div[@id="widget_breadcrumb"]/ul/li/a/text()').extract()
        loader.add_value('category', category[-1])
                
        img = hxs.select('//img[@id="productMainImage"]/@src').extract()
        if img:
            loader.add_value('image_url', img[0])

        loader.add_value('brand', 'lego')
        shipping_cost = hxs.select('//a[@href="#pdp_delivery_return_section" and contains(text(), "Thuisbezorgd")]/text()').extract()
        if shipping_cost:
            loader.add_value('shipping_cost', shipping_cost[0].replace(',', '.'))

        yield loader.load_item()
