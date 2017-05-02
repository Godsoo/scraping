from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.base_spiders.primary_spider import PrimarySpider

from crcitem import CRCMeta

from scrapy import log


class MerlinCyclesSpider(PrimarySpider):
    name = 'crc-merlincycles.com'
    allowed_domains = ['merlincycles.com']
    start_urls = ('http://www.merlincycles.com/',)

    csv_file = 'merlincycles.com_crawl.csv'

    def start_requests(self):
        url = 'http://www.merlincycles.com/ajax/Regional/setRegionalData/'
        yield FormRequest(url, formdata={'country':'33', 'currency':'1'})

    def parse(self, response):
        yield Request('http://www.merlincycles.com', dont_filter=True, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories_urls = hxs.select('//div[@id="merlin-nav"]//a/@href').extract()
        for url in categories_urls:
            yield Request(response.urljoin(url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories_urls = hxs.select('//ol[@class="subCategories"]/li/a/@href').extract()
        for url in categories_urls:
            yield Request(url, callback=self.parse_product_list)

        products_urls = hxs.select('//ul[@class="products"]/li/a/@href').extract()
        for url in products_urls:
            yield Request(url, callback=self.parse_product)

        next = hxs.select('//a[@class="next s"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_id = hxs.select('//div[contains(@class, "productContainer")]/@data-product-id').extract()[0]
        image_url = hxs.select('//div[@id="thumbnails"]/div/a/img/@src').extract()
        category = response.css('.breadcrumb span::text').extract()[-2]
        main_name = ''.join(hxs.select('//h1[@class="product-title"]/text()').extract())
        brand = hxs.select('//li[@class="brand"]/a/span/text()').re('About (\w+)')
        sku = ''.join(hxs.select('//div[@class="stockCode"]/text()').extract()).strip()

        options = hxs.select('//div[contains(@id, "productOption")]/ul[@role="menu"]/li')
        for option in options:
            product_loader = ProductLoader(item=Product(), selector=option)
            option_id = option.select('@data-id').extract()[0]
            product_loader.add_value('brand', brand)

            product_loader.add_value('category', category)
            name = ''.join(option.select('a/span[@class="title"]/text()').extract())
            option_name = ''.join(option.select("./preceding::div[@class='product-option-group'][1]/strong/text()").extract())
            if name == main_name:
                name = main_name
            else:
                name = main_name + ' ' + name

            name = name + ' ' + option_name if option_name else name
            product_loader.add_value('name', name)
            product_loader.add_value('url', response.url)
            identifier = product_id + '-' + option_id
            product_loader.add_value('identifier', identifier)

            # product_loader.add_value('brand', brand)
            product_loader.add_value('sku', sku)
            stock = option.select('./@data-stock').extract()


            rrp = option.select('./@data-rrp').extract()
            rrp = str(extract_price(rrp[0])) if rrp else ''
            price = option.select('./@data-merlin-price').extract()
            if price:
                price = '{0:.2f}'.format(float(price[0]))
                product_loader.add_value('price', price)

            in_stock = stock[0] == 'inStock' if stock else None
            if not in_stock:
                product_loader.add_value('stock', 0)

            product_loader.add_value('image_url', image_url)
            product = product_loader.load_item()
            metadata = CRCMeta()
            metadata['rrp'] = rrp
            product['metadata'] = metadata
            yield product

        if not options:
            identifier = product_id + '-0'
            stock = hxs.select('//div[@class="productContainer"]//span[@class="inStock"]')
            rpp = hxs.select('//div[@class="productContainer"]//span[@class="rrp"]/span/span[@class="price"]/text()').extract()
            price = hxs.select('//meta[@itemprop="price"]/@content').extract()

            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('category', category)
            product_loader.add_value('name', main_name)
            product_loader.add_value('sku', sku)
            product_loader.add_value('url', response.url)
            product_loader.add_value('price', price)
            product_loader.add_value('brand', brand)
            product_loader.add_value('image_url', image_url)
            if not stock:
                product_loader.add_value('stock', 0)

            product = product_loader.load_item()
            metadata = CRCMeta()
            metadata['rrp'] = extract_price(rpp[0]) if rpp else ''
            product['metadata'] = metadata
            yield product


