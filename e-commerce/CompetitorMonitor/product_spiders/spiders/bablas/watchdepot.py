from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc

from product_spiders.items import Product
from bablas_item import ProductLoader


class WatchDepotSpider(BaseSpider):
    name = 'watchdepot.co.uk'
    allowed_domains = ['joshuajamesjewellery.co.uk']
    start_urls = ('http://www.joshuajamesjewellery.co.uk/products/watches-all.html', )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_urls = hxs.select(u'//div/a[@itemprop="name" or @itemprop="url"]/@href').extract()
        next_page = hxs.select('//div[@id="view_more_wrapper"]//a/@href').extract()

        for url in product_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//input[@name="additems[]"]/@value').extract()
        if not identifier:
            return

        category = hxs.select('//div[@id="breadcrumb"]/a/text()').extract()[1:-1]
        loader.add_value('identifier', identifier)
        loader.add_xpath('name', u'//h1[@itemprop="name"]/text()')
        brand = hxs.select('//div[@id="leftcolumn"]/h2/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', hxs.select('//div[@itemprop="description"]/p/small/text()').re("Product Code: (.*)"))
        loader.add_value('url', response.url)
        price = hxs.select('//span[@itemprop="price"]/span/text()').extract()
        if not price:
            price = hxs.select('//*[@itemprop="price"]/text()').extract()
        loader.add_value('price', price)
        image = hxs.select(u'//img[@itemprop="image"]/@src').extract()
        image = image[0] if image else ''
        loader.add_value('image_url', urljoin_rfc(get_base_url(response), image))

        if hxs.select("//div[@id='moreinfowrapper']//td[contains(text(),'Delivered in')]"):
            loader.add_value('stock', 1)
        else:
            if not hxs.select('//link[@itemprop="availability" and contains(@href, "InStock")]'):
                loader.add_value('stock', 0)
            else:
                stock = hxs.select('//link[@itemprop="availability" and contains(@href, "InStock")]/../strong/text()').extract()
                if stock:
                    loader.add_value('stock', stock[0])
        yield loader.load_item()
