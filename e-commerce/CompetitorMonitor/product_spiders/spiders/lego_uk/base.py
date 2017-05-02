import re

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class BaseToysSpider(BaseSpider):
    name = 'legouk-base.com'
    allowed_domains = ['base.com']
    start_urls = []
    _re_sku = re.compile('(\d\d\d\d?\d?)')

    def start_requests(self):
        yield Request('http://www.base.com/cb/setcurrency.ashx?currency=GBP',
                      callback=self.parse_currency)

    def parse_currency(self, response):
        yield Request('http://www.base.com/toys/pg142/bn70000/default.htm?bt=a%3a1%3a260304&gr=2&filter=%2ca%3a403%3a33'
                      '3563')

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        next_page = hxs.select(u'//div[contains(text(),"Page")]/a[contains(text(),"Next")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]))

        products = hxs.select(u'//div[@class="title"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select('//div[@class="product-main-title product-main"]/div/h1/text()').extract()
        if not name:
            name = hxs.select(u'//div[@class="header-section"]/h1/text()').extract()
        if not name:
            self.log('ERROR: no product NAME found! URL:{}'.format(response.url))
        else:
            name = name[0].strip()
            loader.add_value('name', name)

        sku = ''
        prod_id = hxs.select(u'//div[@id="main_frame"]/div/div/text()').re('Catalogue No: (.*)')
        if 'LEGO' in prod_id[0]:
            sku = prod_id
            if '_' not in prod_id[0] and '-' not in prod_id[0]:
                prod_id = self._re_sku.findall(prod_id[0])
                sku = prod_id
            

            
        loader.add_value('identifier', prod_id[0].strip())
        loader.add_value('url', response.url)

        price = ''.join(hxs.select(u'//span[@class="price"]/text()').extract()).strip()
        if not price:
            self.log('ERROR: no product PRICE found! URL:{}'.format(response.url))
            return
        if price:
            loader.add_value('price', price)

        product_image = hxs.select(u'//img[@id="mainImage"]/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            loader.add_value('image_url', image)

        if sku:
            loader.add_value('sku', sku[0])

        loader.add_value('brand', 'Lego')
        yield loader.load_item()
