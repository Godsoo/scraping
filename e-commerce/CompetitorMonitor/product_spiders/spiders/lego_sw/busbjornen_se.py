from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class BusbjornenSpider(BaseSpider):
    name = 'busbjornen.se'
    allowed_domains = ['busbjornen.se']
    start_urls = ['http://www.busbjornen.se/leksaker/lego']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for cat in hxs.select('//div[@class="PLdivUKatLinks"]/a[position()>1]'):
            yield Request(urljoin_rfc(get_base_url(response), cat.select('./@href').extract()[0]),
                          callback=self.parse_pages,
                          meta={'category': cat.select('./text()').extract()[0]})

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//a[@class="PLProduktRubrik"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//input/@prod')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_value('price', ''.join(hxs.select('//span[@class="VPPris"]/text()').extract()).replace(' ', '')) 
        if not loader.get_output_value('price'):
            loader.add_value('price', ''.join(hxs.select('//span[@class="VPKampanjPris"]/text()').extract()).replace(' ', '')) 
        sku = ''.join(hxs.select('//h1/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_value('category', response.meta.get('category'))

        img = hxs.select('//img[@class="VPProdImage1"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        loader.add_value('shipping_cost', '29')
        try:
            loader.add_value('stock',
                re.search('(\d+)', ''.join(hxs.select('//span[starts-with(@class,"VPLagersaldo")]/text()').extract())).groups()[0]
                )
        except:
            pass

        yield loader.load_item()
