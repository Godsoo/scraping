import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from productloader import load_product
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import FormRequest
from product_spiders.utils import extract_price


class WestendDJ(BaseSpider):
    name = 'westenddj.co.uk'
    allowed_domains = ['westenddj.co.uk', 'www.westenddj.co.uk']
    start_urls = ('http://www.westenddj.co.uk',)
    download_delay = 5

    def parse_products(self, response):

        hxs = HtmlXPathSelector(response)

        try:
            category = hxs.select('//div[contains(@class, "breadcrumbs")]/nav/ul/li/text()').extract().pop().strip()
        except:
            category = ''

        for product in hxs.select('//div[@class="category-products"]/ul/li'):
            try:
                url = product.select('.//a[contains(@class, "product-link")]/@href').extract().pop()
                yield Request(url, callback=self.parse_product, meta={'category': category})
            except Exception, e:
                self.log('Error in %s | %s: %s' % (response.url, name, e))
                pass

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        # categories
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//nav[@id="nav"]/ul/li//a/@href').extract()
        for url in category_urls:
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        # next page
        next_page = hxs.select('//li/a[contains(@class, "i-next")]/@href').extract() 	
        if next_page:
            yield Request(next_page.pop(), callback=self.parse_category)

        # products
        for p in self.parse_products(response):
            yield p

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = ''.join(hxs.select('//h1[@itemprop="name"]/text()').extract())
        description = ' '.join(''.join(hxs.select('//p[@itemprop="description"]//text()').extract()).split())
        price = response.xpath('//div[contains(@class, "inner")]//span[@itemprop="price"]/span[@class="price"]/text()').extract()
        if not price:
            price = response.xpath('//div[contains(@class, "inner")]//span[@itemprop="lowPrice"]/text()').extract() or response.xpath('//script/text()').re('"priceWithTax":(.+?),')
        price = extract_price(price[0]) if price else '0.0'
        brand = hxs.select('//img[@itemprop="brand"]/@alt').extract()

        image = hxs.select('//img[@itemprop="image"]/@src').extract()
        out_of_stock = hxs.select('//span[@class="availability out-of-stock"]')
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('brand', brand)
        if image:
            loader.add_value('image_url', image[0])
        loader.add_value('identifier', hxs.select('//input[@name="product"]/@value').extract()[0])
        category = hxs.select('//div[contains(@class, "breadcrumbs")]/nav/ul/li/a/text()').extract()[-1]
        loader.add_value('category', response.meta.get('category', ''))
        loader.add_value('shipping_cost', '5.00' if float(loader.get_output_value('price')) < 51.00 else '0.00')
        if out_of_stock:
            loader.add_value('stock', 0)
        yield loader.load_item()
        
