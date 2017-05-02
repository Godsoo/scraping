from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class KlevringsSpider(BaseSpider):
    name = 'klevrings.se'
    allowed_domains = ['klevrings.se']
    start_urls = ['http://klevrings.se/search?q=LEGO%20DUPLO&p=2']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        #for category in hxs.select('//li[@class="current many"]/ul[@class="categories"]/li[@class="not-current"]/a/@href').extract():
            #yield Request(urljoin_rfc(base_url, category))

        for product in hxs.select('//article[contains(@class, "product")]//a/@href').extract():
            if 'lego-wear-' not in product:
                yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        for page in hxs.select('//ul[@class="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, page))


    def parse_product(self, response):
        import re
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', 'substring-after(//div[@class="code"]/text(), " ")')
        if not loader.get_output_value('identifier'):
            loader.add_xpath('identifier', 'substring-after(//*/@data-code, " ")')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        sku = ''.join(hxs.select('//h1/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_xpath('price', '//span[@itemprop="price"]/text()')
        loader.add_xpath('category', '//div[@class="paths"]/ul/li[1]/span[last()]//a/text()')

        img = hxs.select('//div[@class="images"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        loader.add_value('shipping_cost', '49')
        if hxs.select('//select[@name="num"]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        yield loader.load_item()
