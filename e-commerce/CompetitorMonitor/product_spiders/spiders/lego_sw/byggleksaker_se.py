from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class ByggleksakerSpider(BaseSpider):
    name = 'byggleksaker.se'
    allowed_domains = ['byggleksaker.se']
    start_urls = ['http://www.byggleksaker.se/lego']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for cat in hxs.select('//div[@id="subCategory"]//a'):
            yield Request(urljoin_rfc(get_base_url(response), cat.select('./@href').extract()[0]),
                          callback=self.parse_pages,
                          meta={'category': cat.select('./text()').extract()[-1]})

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[@class="image"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')
        loader.add_xpath('price', '//div[@class="buybutton"]//nobr//text()') 
        sku = ''.join(hxs.select('//td[contains(text(), "Artikelkod")]/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_value('category', response.meta.get('category'))

        img = hxs.select('//meta[@property="og:image"]/@content').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
            loader.add_value('identifier', loader.get_output_value('image_url').split('/')[-1].split('-')[0])
        else:
            loader.add_value('identifier', loader.get_output_value('url').split('/')[-1])

        loader.add_value('brand', 'lego')
        if loader.get_output_value('price') > 1500:
            loader.add_value('shipping_cost', '0')
        else:
            loader.add_value('shipping_cost', '49')
        if hxs.select('//div[@class="buybutton" and @onclick]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        yield loader.load_item()
