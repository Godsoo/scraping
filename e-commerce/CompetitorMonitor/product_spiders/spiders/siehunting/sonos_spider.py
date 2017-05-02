import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class SonosSpider(BaseSpider):
    name = 'sonos.dk'
    allowed_domains = ['sonos.dk']
    start_urls = ['http://www.sonos.dk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories =  hxs.select('//ul[@class="b_main"]/li/a/@href').extract() + hxs.select('//ul[@class="b_main"]/li/ul/li/a/@href').extract()
        for category in categories:
            url =  urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="product"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                url = urljoin_rfc(get_base_url(response),  product.select('div/div/div/div[@class="name"]/a/@href').extract()[0])
                yield Request(url, callback=self.parse_product, meta={u'requested': False})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        options = hxs.select('//div[@class="choosevariant"]/div/dl/dd/select')
        
        if options and (not response.meta[u'requested']):
                option_values = options.select('option[@value!=0]/@value').extract()
                id = options.select('@name').extract()[0]
                viewstate = hxs.select('//*[@id="__VIEWSTATE"]/@value').extract()[0]
                eventvalidation = hxs.select('//*[@id="__EVENTVALIDATION"]/@value').extract()[0]
                for option_value in option_values:
                    formname = u'aspnetForm'
                    formdata = {id : option_value,
                                u'__EVENTTARGET': id,
                                u'__EVENTARGUMENT': u'',
                                u'__EVENTVALIDATION': eventvalidation,
                                u'__VIEWSTATE': viewstate}
                    request = FormRequest(response.url, formdata=formdata, callback=self.parse_product,
                                                meta={u'requested': True})
                    yield request
        else:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('name', '//div[@class="productpage"]/h1/text()')
            loader.add_value('url', response.url)
            price = ''.join(hxs.select('//div[@class="price left"]/'
                                       'div[@class="current price"]/'
                                       'span[@class="first"]/text()').extract()).replace('.','').replace(',','.')
            if not price:
                price = ''.join(hxs.select('//div[@class="price left"]/'
                                       'div[@class="current price offer"]/'
                                       'span[@class="first"]/text()').extract()).replace('.','').replace(',','.')
                if not price:
                    price = ''.join(hxs.select('//div[@class="price left"]/span/'
                                       'div[@class="current price"]/'
                                       'span[@class="first"]/text()').extract()).replace('.','').replace(',','.')
            loader.add_value('price', price)
            yield loader.load_item()
        

        
        
