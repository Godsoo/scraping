from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
import re


class BilkaDkSpider(BaseSpider):
    name = 'eurotoys.dk'
    allowed_domains = ['eurotoys.dk']
    start_urls = ('http://www.eurotoys.dk/site/Lego.asp?site=34',
                  'http://www.eurotoys.dk/site/Lego_Duplo.asp?site=33')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        #pagination
        urls = hxs.select('//*[@id="paging"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

        products = hxs.select('//div[contains(@class,"produkt_boks")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            in_stock = product.select('.//div[@class="laegikurv"]/a/@class').extract()[0]
            if in_stock != 'laegivogn':
                product_loader.add_value('stock', 0)
            identifier = product.select('.//div[@class="desc"]/a/@href').extract()[0].partition('&vn=')[2]
            product_loader.add_value('identifier', identifier)
            image_url = product.select('.//div[@class="produkt_img"]//img/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            product_name = product.select('.//div[@class="desc"]/a/text()').extract()[0]
            product_loader.add_value('name', product_name)
            sku_text = ''.join(product.select('.//div[@class="desc"]/text()').extract())
            sku = ''
            for match in re.finditer(r"([\d]+)", sku_text):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            url = product.select('.//div[@class="desc"]/a/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            price = product.select('.//span[@class="pris"]/text()').extract()[0].strip().strip('DKK ')
            price = extract_price(price)
            product_loader.add_value('price', price)
            if price < 1000:
                product_loader.add_value('shipping_cost', 49)
            else:
                product_loader.add_value('shipping_cost', 0)
            yield product_loader.load_item()
