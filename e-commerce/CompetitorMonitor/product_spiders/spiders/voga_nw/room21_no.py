from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re


class Room21NoSpider(BaseSpider):
    name = 'voga_nw-room21.no'
    allowed_domains = ['room21.no']
    start_urls = ['http://www.room21.no/']
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="level1"]//ul[@class="child-ul level3"]//a/@href').extract():
            url = url.replace('index.html', 'ALLA/sida.html')
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for product in hxs.select('//div[@class="PT_Wrapper_All"]//div[@class="PT_Wrapper col span_1_of_4"]//div[@class="PT_Beskr"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        if 'Egenskap2' in response.body:
            self.log('SECOND!!!!!!!!')

        has_options = hxs.select('//*[@id="OrderFalt"]//select[@name="Egenskap1"]')

        img = hxs.select('//img[@itemprop="image"]/@src').extract()
        category = hxs.select('//*[@id="breadcrumb"]//a/text()').extract()[1:]
        brand = hxs.select('//*[@id="VarumarkeFalt"]/a/img/@alt').extract()
        brand = brand[0] if brand else ''

        if has_options:
            for match in re.finditer(r"(?sim)Vektor_Rubrikartikel\[\d+\] = '(.*?)';", response.body_as_unicode()):
                loader = ProductLoader(item=Product(), selector=hxs)
                option = match.group(1)
                option = option.split('!div!')
                name = option[2]
                product_identifier = option[4]
                match = re.search(r'<span class="PrisREA">(\d+)<span>', option[1],
                                  re.DOTALL | re.IGNORECASE | re.MULTILINE)
                if match:
                    result = match.group(1)
                else:
                    match = re.search(r'<span class="PrisBOLD">(\d+)<span>', option[1],
                                  re.DOTALL | re.IGNORECASE | re.MULTILINE)
                    if match:
                        result = match.group(1)
                    else:
                        self.log('ERROR!!!! NO price!')
                        result = '0'
                price = extract_price_eu(result)
                stock = option[6]
                if 'Midlertidig utsolgt' in stock:
                    loader.add_value('stock', 0)
                loader.add_value('identifier', product_identifier)
                loader.add_value('sku', product_identifier)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                if img:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                yield loader.load_item()
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            product_identifier = hxs.select('//*[@id="ArtnrFalt"]/text()').extract()[0]
            loader.add_value('identifier', product_identifier)
            loader.add_value('sku', product_identifier)
            loader.add_value('url', response.url)
            loader.add_xpath('name', '//*[@id="ArtikelnamnFalt"]/text()')
            price = ''.join(hxs.select('//*[@id="PrisFalt"]/meta[@itemprop="price"]/@content').extract())
            price = extract_price_eu(price)
            loader.add_value('price', price)
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))
            loader.add_value('category', category)
            loader.add_value('brand', brand)
            stock = hxs.select('//*[@id="LevtidFaltMeta"]/@content').extract()[0].strip()
            if stock == 'Midlertidig utsolgt':
                loader.add_value('stock', 0)
            yield loader.load_item()