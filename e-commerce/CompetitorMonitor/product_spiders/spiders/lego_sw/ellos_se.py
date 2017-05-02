from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import re

from scrapy import log

class EllosSeSpider(BaseSpider):
    name = 'ellos.se'
    allowed_domains = ['ellos.se']
    start_urls = ('http://www.ellos.se/lego_3?rcnt=100&Nao=0',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//*[contains(@class, "productWrapper")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            name = ''.join([s.strip() for s in product.select('.//div[contains(@class, "headlineWrapper")]//text()').extract()])
            product_loader.add_value('name', name)
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            image_url = product.select('.//div[contains(@class, "carouselWrapper")]/img[1]/@data-original').extract()
            if not image_url:
                image_url = product.select('.//img[contains(@class, "productImage")]/@data-original').extract()
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = ''.join(product.select('.//span[@class="price"]//text()').extract()).strip()\
                .replace(',-', '').replace(u'\xa0', '').replace(',', '.')
            product_loader.add_value('price', extract_price(price))
            try:
                url = product.select('.//a[contains(@class, "productLink")]/@href').extract()[0]
            except:
                log.msg('Ignoring product without URL')
                continue
            identifier = re.search(r'/(\d+)\?', url).groups()[0]
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            product = product_loader.load_item()
            yield product
        # parse pagination
        urls = hxs.select('//*[contains(@class, "pagingWrapper")]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)
