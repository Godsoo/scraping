import re
import urlparse
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price

class TyresDirectCoUk(BaseSpider):
    name = 'tyresdirectukcouk'
    allowed_domains = ['tyresdirectuk.co.uk']
    start_urls = ('https://www.tyresdirectuk.co.uk/shop/category/tyres/', 
                  'https://www.tyresdirectuk.co.uk/shop/category/wheels/')

    exclude_word = 'DOT'
    
    def __init__(self, *args, **kwargs):
        super(TyresDirectCoUk, self).__init__(*args, **kwargs)

    def _parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        # categories and subcategories
        #brands = hxs.select('//div[@class="content"]/div[@class="brandbox"]/div/a[strong]')
        #brand_list = [' '.join(b.split()) for b in brands.select('strong/text()').extract()]
        #for brand in brands:
        #    url = urljoin_rfc(get_base_url(response), brand.select('@href').extract()[0])
        #    yield Request(url, meta={'brands': brand_list})

        sub_categories = hxs.select('//div//span/a/img[contains(@alt, "Tyres")]/../@href').extract()
        for url in sub_categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta)

        # next page
        # next_page = 
        # if next_page:
        #     url = urljoin_rfc(self.URL_BASE, next_page[0])
        #   yield Request(url)

        # products
        for product in self.parse_product(response):
            yield product

        next_page = response.xpath('//li[@class="next_page"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]), meta=response.meta)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        for url in response.xpath('//nav[contains(@class, "pagination")]/a/@href').extract():
            yield Request(url)
            
        #brand = re.search(' (\w+) Tyres', ''.join(hxs.select('//h1/text()').extract()))
        #brand = brand.group(1) if brand else ''

        products = response.xpath('//div[@id="content"]/ul/li[contains(@class, type-product)]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//h3/a/text()').extract()[0]
            product_loader.add_value('name', name)
            tyre_details = ''.join(product.xpath('./div[2]//*[not(@type="text/css")]/text()').extract())
            product_loader.add_value('name', tyre_details)
            url = product.select('.//a/@href').extract()[0]
            url = urljoin_rfc(get_base_url(response), url)
            product_loader.add_value('url', url)

            #parsed = urlparse.urlparse(url)
            #params = urlparse.parse_qs(parsed.query)
            identifier = product.select('./@class').re('post-(\d+?) ')
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('sku', identifier)

            #product_brand = ''
            #for brand in meta.get('brands'):
            #    if brand.upper() in name.upper() or brand.split()[0].upper() in name.upper():
            #        product_brand = brand
            #        break
 
            #product_loader.add_value('category', product_brand)
            #product_loader.add_value('brand', product_brand)

            image_url = product.css(".featured-image, .crossfade-images").xpath('img/@src').extract()
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))
            price = product.select('.//span[@class="price"]/span[@class="amount"]/text()').extract()
            if price:
                price = extract_price(price[0]) + Decimal(5.25)
                product_loader.add_value('price', price)
            else:
                product_loader.add_value('price', 0)

            #out_of_stock = product.select('div//p/b[contains(text(), "Awaiting Stock")]')
            #if out_of_stock:
            #    product_loader.add_value('stock', 0)
            #    item = product_loader.load_item()
            #    yield Request(item['url'], callback=self.parse_price, meta={'item':item})
            #else:
            item = Product(product_loader.load_item())
            if self.exclude_word not in item['name']:
                yield Request(url, callback=self.parse_brand, meta={'item':item})

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']
        brand = hxs.select('//span[@class="pa_brand"]/span[@class="attribute-value"]/text()').extract()
        if brand:
            brand = brand[0]
            item['brand'] = brand
            item['category'] = brand
        yield item
        
    def parse_price(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']

        price = hxs.select('//span[@id="price"]/text()').extract()
        item['price'] = extract_price(price[0])+Decimal(5.25) if price else 0 
        yield item
        

