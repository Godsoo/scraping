import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

class Pharmacy2USpider(ProductCacheSpider):
    name = 'pharmacy2u.co.uk'
    allowed_domains = ['pharmacy2u.co.uk']
    start_urls = ('http://www.pharmacy2u.co.uk/Pharmacy.aspx',)

    def _start_requests(self):
        yield Request('http://www.pharmacy2u.co.uk/cold-and-flu-s653.html', callback=self.parse_cat, meta={'product': Product()})
        return
        yield Request('http://www.pharmacy2u.co.uk/erectile-dysfunction-s844.html', callback=self.parse_cat, meta={'product': Product()})

    def parse(self, response):
        yield Request('https://www.pharmacy2u.co.uk/atozbrands.aspx', callback=self.parse_brands)
        for cat in response.css('.health a::attr(href)').extract():
            yield Request(response.urljoin(cat), callback=self.parse_cat)

    def parse_brands(self, response):
        for letter in response.css('.letter ::attr(href)').extract():
            yield Request(response.urljoin(letter), callback=self.parse_brand)
            
    def parse_brand(self, response):
        for brand in response.css('.brands a::attr(href)').extract():
            yield Request(response.urljoin(brand), callback=self.parse_cat)
        
    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        for productxs in response.css('.product'):
            product = Product()
            price = productxs.css('.price ::text').extract_first()
            product['price'] = extract_price(price) if price else 0
            if product['price']:
                product['stock'] = 1
            else:
                product['stock'] = 0
            
            url = productxs.xpath('.//a/@href').extract_first()
            if not url:
                continue
            url = response.urljoin(url).replace('/product/', '/')
            request = Request(url, callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        total_products = response.css('#TotalProducts ::attr(value)').extract_first()
        if not total_products:
            return
        category_id = response.css('#CategoryGUID::attr(value)').extract_first()
        url = 'https://www.pharmacy2u.co.uk/product/categoryproducts?categoryguid=%s&pagenumber=%d&resultsperpage=24&sortorder=bm'
        for page_number in xrange(int(total_products)/24):
            yield Request(url %(category_id, page_number+1), callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        prescription = response.xpath('//ul[@itemprop="description"]/li[contains(text(), "Prescription required")]')
        if not prescription:
            prescription = response.xpath('//strong[text()="Prescription only"]')

        if not prescription:
            loader = ProductLoader(item=response.meta['product'], selector=hxs)
            identifier = response.css('#MainProduct_Product_ProductGUID ::attr(value)').extract() or response.xpath('//span[@class="hdnProductGuid"]/text()').extract()
            if not identifier:
                return
            loader.add_value('identifier', identifier)
            loader.add_xpath('url', '//link[@rel="canonical"]/@href')
            loader.add_value('url', response.url)
            loader.add_xpath('name', '//h1/text()')
            loader.add_xpath('sku', '//label[@class="prodCodeSize"]/b/text()')
            
            category = response.css('.breadcrumb').xpath('//span[@itemprop="title"]/text()').extract()[1:-1]
            loader.add_value('category', category)

            img = response.css('.slider-main img::attr(src)').extract() or response.css('.img-responsive ::attr(src)').extract()
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

            brand = ''.join(response.xpath('//a[@class="abrandPLink"]//text()').extract())
            brand = brand.replace('See More ', '').replace(' Products', '').strip()
            if not brand:
                brand = loader.get_output_value('name').split()[0]
            if brand:
                loader.add_value('brand', brand)
            yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        return item
        if item.get('price', 0) < 40:
            item['shipping_cost'] = 3.49
        else:
            item['shipping_cost'] = 0
