import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

PROXIES = ['http://23.19.154.246:3128',
           'http://23.19.154.247:3128',
           'http://23.19.154.248:3128',
           'http://23.19.154.249:3128',
           'http://23.19.154.250:3128',
           'http://23.19.188.246:3128',
           'http://23.19.188.247:3128',
           'http://23.19.188.248:3128',
           'http://23.19.188.249:3128',
           'http://23.19.188.250:3128']

class CDiscountBaseSpider(BaseSpider):
    name = 'test_cdiscount.com'
    allowed_domains = ['www.cdiscount.com', 'cdiscount.com']
    start_urls = (u'http://www.cdiscount.com/maison/bricolage-outillage/l-11704.html',
                  u'http://www.cdiscount.com/maison/bricolage-outillage/outillage-de-jardin/v-1170414-1170414.html',
                  u'http://www.cdiscount.com/electromenager/aspirateur-nettoyeur-vapeur/v-11014-11014.html')

    def _proxyRequest(self, *args, **kwargs):
        meta = {'proxy': self.proxy}
        if 'meta' in kwargs:
            kwargs['meta'].update(meta)
        else:
            kwargs['meta'] = meta
        return Request(*args, **kwargs)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            self.log('ERROR: BAD HtmlResponse!!! URL:{}'.format(response.url))
            return
        hxs = HtmlXPathSelector(response)

        # logic to find categories
        # find subcats for Outilage Jardin
        categories = hxs.select('//div[contains(@class,"bg_U15 menugroup") and contains(@alt,"Jardin") and contains(@alt,"Outillage")]//div[@class="jsGroup"]//ul[@class="tree"]//a/@href').extract()
        # find subcats for Aspirateurs
        categories += hxs.select('//div[contains(@class,"bg_U4 menugroup") and contains(@alt,"Entretien") and contains(@alt,"maison")]//div[@class="jsGroup"]//ul[@class="tree"]//a/@href').extract()

        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield self._proxyRequest(url)

        # products new logic
        products = hxs.select(u'//div[@id="productList"]//div[contains(@class,"plProductView")]')
        if products:
            for product in products:
                product_loader = ProductLoader(item=Product(), selector=product)
                product_loader.add_xpath('url', './/a[contains(@class,"plPrName")]/@href')
                product_loader.add_xpath('name', './/a[contains(@class,"plPrName")]/text()')
                product_loader.add_xpath('category', '//div[@class="productListTitle"]/h1/text()')
                product_loader.add_xpath('image_url', './/div[contains(@class, "plProductImg")]//img/@data-src')
                product_loader.add_xpath('sku', './@data-sku')
                product_loader.add_xpath('identifier', './/input[contains(@name, "ProductPostedForm.ProductId")]/@value')
                price = product.select(u'.//div[contains(@class,"priceContainer")]/div[contains(@class,"priceM")]/text()').extract()
                if price:
                    decimals = product.select(u'//div[contains(@class,"priceContainer")]/div[contains(@class,"priceM")]/sup/text()').re(u'(\d+)')
                    if decimals:
                        price = price[0] + '.' + decimals[0]
                product_loader.add_value('price', price)
                if product_loader.get_output_value('name') and product_loader.get_output_value('price'):
                    yield product_loader.load_item()

        # pagination
        next_page = hxs.select(u'//ul[@class="PaginationButtons"]//a[contains(text(),"Suivant")]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield self._proxyRequest(next_page)