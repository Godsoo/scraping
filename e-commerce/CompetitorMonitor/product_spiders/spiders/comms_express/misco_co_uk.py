from urllib import quote as url_quote

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.comms_express.utils import CommsBaseSpider

class MiscoSpider(CommsBaseSpider):
    name = 'misco.co.uk'
    allowed_domains = ['misco.co.uk']

    def keyword_handle(self, keyword):
        return keyword.replace("/", " ").replace(".", "[dot]")

    def start_requests(self):
        for i, search in enumerate(self.whitelist):
            self.log('Searching: %s' % search)
            yield Request('http://www.misco.co.uk/Search/Keyword/%s' % url_quote(self.keyword_handle(search), ''),
                          callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        warning = ' '.join(hxs.select('//span[@class="txt-bold" and contains(.., "Sorry, no results found")]/text()').extract())
        if warning:
            self.log(warning)
            return

        warning = hxs.select('//div[@id="container"]//span[contains(text(), "Sorry, this product") and contains(text(), " is no longer available.")]/text()').extract()
        if warning:
            self.log(warning[0])
            return

        many = hxs.select('//div[contains(@class,"ProductListing")]//a[contains(@class, "ProductHeader")]/@href').extract()
        if many:
            for url in many:
                yield Request(urljoin(get_base_url(response), url), callback=self.parse_product)
            next = hxs.select('//a[text()="Next" and contains(@href, "list")]/@href').extract()
            if next:
                yield Request(next[0], callback=self.parse_product)

            return

        info = ' '.join(hxs.select('//span[@class="pcsBrand" and contains(., "Manufacturer/No:")]//text()').extract()[2:])
        if not info:
            return
        info = info.replace('Manufacturer/No:', '')
        brand, sku = info.split('  / ')
        loader.add_value('identifier', sku)

        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_xpath('price', '//span[@class="size20 b"]//text()')
        loader.add_value('sku', sku.strip())
        loader.add_xpath('category', '//span[position()=last()]/a[contains(@class,"blackLink") and position()=last()]/text()')

        img = hxs.select('//a[@class="MiscoZoom"]/@href').extract()
        if not img:
            img = hxs.select('//img[@id="noimage"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin(get_base_url(response), img[0]))

        loader.add_value('brand', brand.strip())
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', '1.99')
        else:
            loader.add_value('shipping_cost', '7.07')

        #if hxs.select('//b[contains(text(), "In Stock") or contains(text(), "In stock") or contains(text(), "Buy now")]'):
        loader.add_value('stock', '1')
        #else:
            #loader.add_value('stock', '0')

        self.yield_item(loader.load_item())
        return
