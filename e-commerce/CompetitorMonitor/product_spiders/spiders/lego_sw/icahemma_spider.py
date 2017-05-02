import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu as extract_price


class IcahemmaSpider(BaseSpider):
    name = 'legosw-icahemma.se'
    allowed_domains = ['icahemma.se']
    start_urls = ('http://www.icahemma.se/lego-c-673-1.aspx',)

    re_sku = re.compile('(\d\d\d\d\d?)')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="ProductName"]/h3/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': 'Lego'})
        
        next = hxs.select('//a[@class="ListPagingControlPagerNext"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_category)

        categories = hxs.select('//li[contains(@class, "has-subcategories") and a/text()="Lego"]/ul[@class="lv3"]/li/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        category = hxs.select('//div[@class="CategoryPageHeader"]/h1/text()').extract()[0]

        products = hxs.select('//div[@class="ProductName"]/h3/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})
        
        next = hxs.select('//a[@class="ListPagingControlPagerNext"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_name = hxs.select('//h1[contains(@class, "product-name")]/text()').extract()[0].strip()
        image_url = hxs.select('//img[contains(@id, "Product_imgMainImage")]/@src').extract()
        image_url = image_url[0] if image_url else ''
        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        product_loader.add_value('name', product_name)
        product_loader.add_value('brand', 'LEGO')
        product_loader.add_value('category', response.meta['category'])
        product_loader.add_value('url', response.url)
        identifier = hxs.select('//input[contains(@id, "tbHiddenProductID")]/@value').extract()[0]
        product_loader.add_value('identifier', identifier)
        sku = self.re_sku.findall(product_name)
        product_loader.add_value('sku', sku)
        price = ''.join(hxs.select('//span[@class="PriceAmount"]/span[contains(@class, "price")]/text()').extract()[0].split())
        '''
        if not price:
            price = hxs.select('//td[@id="price"]/span/text()').extract()
        price = price[0].replace(u':-', '')
        '''
        product_loader.add_value('price', extract_price(price))
        product_loader.add_value('shipping_cost', '49')
        in_stock = 'I LAGER' in ''.join(hxs.select('//span[@class="webshop-stock-status"]/span/text()').extract()).upper()
        if not in_stock:
            product_loader.add_value('stock', 0)
        '''
        stock = hxs.select('//span[@class="instock"]/strong/text()').extract()
        if stock:
            if stock[0].strip() != 'Finns i lager.':
                stock = 0
        else:
            stock = 0
        if not stock:
            product_loader.add_value('stock', 0)
        '''
        product = product_loader.load_item()
        yield product
