from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu, extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class DiscshopSpider(BaseSpider):
    name = 'discshop.se'
    allowed_domains = ['discshop.se']
    start_urls = ['http://www.discshop.se/products.php?&q=lego&post_type=film&page_size=200',
    'http://www.discshop.se/products.php?&q=lego&post_type=spel&page_size=200',
    'http://www.discshop.se/products.php?&q=lego&post_type=poster&page_size=200']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[@class="msec"]//h3/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//input[@id="product_id"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        sku = ''.join(hxs.select('//h1/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            sku = response.xpath('//input[@id="product_productID"]/@value').extract()
            if sku:
                loader.add_value('sku', sku[0].strip())
            else:
                self.log('No SKU for %s' % (response.url))
        loader.add_xpath('price', '//*[@itemprop="price"]/text()')
        loader.add_xpath('category', '//ul[@id="mnu_main"]/li[contains(@class, "selected")]//a/text()')

        img = hxs.select('//div[@class="img"]//a/@href').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        if loader.get_collected_values('price') and loader.get_collected_values('price')[0] < 600:
            loader.add_value('shipping_cost', '29')
#        loader.add_value('shipping_cost', '49')
#        loader.add_value('stock', '0')
 
        prod = loader.load_item()
        if prod.get('price'):
            yield prod
        else:
            for opt in hxs.select('//div[@class="cont"]//a/@href').extract():
                yield Request(urljoin_rfc(get_base_url(response), opt), callback=self.parse_product, meta=response.meta)
         
