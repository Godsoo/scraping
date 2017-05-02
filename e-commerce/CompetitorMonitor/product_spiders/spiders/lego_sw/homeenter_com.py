from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class HomeenterSpider(BaseSpider):
    name = 'homeenter.com'
    allowed_domains = ['homeenter.com']
    start_urls = ['http://www.homeenter.com/33131/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//*[@class="mainarea"]//div/a[contains(text(), "Se fler")]')
        for cat in categories:
            yield Request(urljoin_rfc(base_url, cat.select('@href').extract()[0]),
                          callback=self.parse_pages,
                          meta={'category': cat.select('text()').re(r'Se fler (.*)')[0].replace('>>>', '').strip()})

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//a/img[@class="PIWC"]/../@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_value('identifier', [x for x in response.url.split('?')[0].split('/') if x][-1])
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        sku = ''.join(hxs.select('//h1/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_value('price', extract_price_eu(hxs.select('//b[@class="priceFPNormal_special"]/text()')[0].extract()))
        loader.add_value('category', response.meta.get('category'))

        img = hxs.select('//a[@id="mbpicturepos0"]/@href').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
#        loader.add_value('shipping_cost', '49')
#        loader.add_value('stock', '0')

        yield loader.load_item()
