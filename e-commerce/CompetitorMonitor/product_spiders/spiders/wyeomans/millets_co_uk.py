from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import (Product,
        ProductLoaderWithNameStrip as ProductLoader)

class MilletsSpider(BaseSpider):
    name = 'millets.co.uk'
    allowed_domains = ['millets.co.uk']
    start_urls = ['http://www.millets.co.uk']

    def _start_requests(self):
        yield Request('http://www.millets.co.uk/mens/073677-regatta-mens-telman-3-in-1-jacket.html', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//div[@class="template_nav_main"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)

        category = hxs.select('//h1[@class="title"]//text()').extract()

        for cat in hxs.select('//div[contains(@class, "productitem")]//h2//a/@href').extract():
            meta = response.meta.copy()
            meta['category'] = category
            yield Request(urljoin_rfc(get_base_url(response), cat),
                          callback=self.parse_product,
                          meta=meta)

        for cat in hxs.select('//div[@class="productlist_paging_container"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_products, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//input[@id="product_id"]/@value')
        loader.add_xpath('sku', 'substring-after(//div[@class="details_code"]/strong/text(),"#")')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')
        loader.add_xpath('name', '//option[@selected="selected"]/text()')
        loader.add_xpath('price', '//span[@class="details_price_now"]//text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', '//p[@class="details_price"]//text()')
        loader.add_value('category', response.meta['category'])
        img = hxs.select('//a[@id="zoom1"]/img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        brand = hxs.select('//th/label[contains(text(),"Brand:")]/../../td/text()').extract()
        loader.add_value('brand', brand)

        if loader.get_output_value('price'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')
        if loader.get_output_value('price') < 50.00:
            loader.add_value('shipping_cost', '3.99')
        else:
            loader.add_value('shipping_cost', '0')

        item = loader.load_item()
        if item.get('identifier'):
            sizes = hxs.select('//ul[@rel="size"]/li/a')
            if sizes:
                for size in sizes:
                    prod_opt = Product(item)
                    prod_opt['name'] += ' ' + ''.join(size.select('./text()').extract())
                    prod_opt['identifier'] += '-' + ''.join(size.select('./@href').extract())
                    yield prod_opt
            else:
                yield item
