from urllib import quote as url_quote
from urlparse import urljoin

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.comms_express.utils import CommsBaseSpider


class NetstoreDirectSpider(CommsBaseSpider):
    name = 'netstoredirect.com'
    allowed_domains = ['netstoredirect.com']

    def start_requests(self):
        for i, search in enumerate(self.whitelist):
            self.log('Searching: %s' % (search))
            yield Request('http://www.netstoredirect.com/search?search_query=%s&orderby=position&orderway=desc&submit_search=&n=75' % url_quote(search, ''), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        warning = ''.join(hxs.select('//p[@class="alert alert-warning"]/text()').extract())
        if warning:
            self.log(warning)
            return

        many = hxs.select('//a[@class="product_img_link"]/@href').extract()
        if many:
            for url in many:
                yield Request(url, callback=self.parse_product)
            # Next page
            for url in hxs.select('//li[contains(@class, "next")]/a/@href').extract():
                yield Request(url, callback=self.parse_product)
            return

        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//p[@id="product_reference"]/span[@itemprop="mpn"]/@content').extract().pop()
        if not identifier:
            return
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        price = ''.join(hxs.select('//span[@id="our_price_display_ex"]/text()').extract()).strip()
        loader.add_value('price', price)
        loader.add_xpath('sku', '//p[@id="product_reference"]/span[@itemprop="mpn"]/@content')
        category = hxs.select('//ul[@class="tree dhtml"]/li/a[contains(@class, "path")]/text()').extract()[:-1]
        loader.add_value('category', category)

        img = hxs.select('//div[@id="image-block"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin(get_base_url(response), img[0]))
        brands = hxs.select('//select[@id="manufacturer_list"]//option/text()').extract()
        word1 = loader.get_output_value('name')
        if not word1:
            return
        word1 = word1.split()[0].lower()
        for brand in brands:
            if brand.lower() == word1:
                loader.add_value('brand', brand)
                break
        else:
            loader.add_value('brand', word1)

        if loader.get_output_value('price') < 60:
            loader.add_value('shipping_cost', '2.50')
        else:
            loader.add_value('shipping_cost', '0')
        if hxs.select('//p[@id="product_condition"]/span[contains(text(), "Out of Stock")]'):
            loader.add_value('stock', '0')
        else:
            loader.add_value('stock', '1')
        self.yield_item(loader.load_item())
        return

