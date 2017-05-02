from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import urlparse
import re

class BambaSpider(BaseSpider):
    name = 'bamba.se'
    allowed_domains = ['bamba.se']
    start_urls = ['https://www.bamba.se/category.html/lego']

    def clear_url(self, url, allowed):
        url = urlparse.urlparse(url)
        params = urlparse.parse_qs(url.query)
        new_params = {}
        for key, val in params.items():
            if key in allowed:
                new_params[key] = val.pop() if val else ""
        return url.path + "?" + "&".join("=".join(x) for x in new_params.items())


    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//a[@rel="product"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)
        for page in hxs.select('//div[@class="pagesbar"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), self.clear_url(page, ['category_id', 'Pagenum'])), callback=self.parse, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//input[@name="ID"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        sku = ''.join(hxs.select('//td/b[contains(text(), "Artikelnummer")]/../text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_xpath('price', '//*[@class="main-price"]/text()')
        loader.add_xpath('category', 'substring-after(//h1/text(), ", ")')

        img = hxs.select('//div[@id="gallery"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
#        loader.add_value('shipping_cost', '49')
        stock = ''.join(hxs.select('//input[contains(@id, "stock_")]/@value').extract())
        if not stock == '0' and stock:
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        yield loader.load_item()
