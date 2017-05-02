import re

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class JohnLewisSpider(BaseSpider):
    name = 'johnlewis.com-travel'
    allowed_domains = ['johnlewis.com']
    start_urls = ['http://www.johnlewis.com/shop-by-brand/antler/c600002542',
                  'http://www.johnlewis.com/shop-by-brand/eastpak/c600002170',
                  'http://www.johnlewis.com/shop-by-brand/samsonite/c600002096',
                  'http://www.johnlewis.com/wenger/brand']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # Samsonite categories
        cats = hxs.select("//div/section/article/h3/a/@href").extract()
        # Eastpak categories
        cats += hxs.select("//div[@id='cq_3cats_nobord']/ul/li/a/@href").extract()
        # Antler categories
        cats += hxs.select('//*[@id="cq-brand-store"]/div/ul//li/a/@href').extract()

        if cats:
            for cat in cats:
                yield Request(
                    url=urljoin_rfc(base_url, cat),
                    callback=self.parse_products
                )
        else:
            yield Request(
                url=response.url,
                dont_filter=True,
                callback=self.parse_products
            )

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//div[@class="pagination"]//a[text()="Next"]/@href').extract()
        if next_page:
            log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> TURN TO NEXT PAGE")
            yield Request(
                    url=urljoin_rfc(base_url, next_page[0]),
                    callback=self.parse_products)

        products = hxs.select("//div[@class='products']/div/article")
        log.msg(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> FOUND %s" % len(products))
        if products:
            for product in products:
                url = urljoin_rfc(base_url, product.select(".//a[@class='product-link']/@href").extract()[0])
                yield Request(url, self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = ' '.join(re.findall(r"[\w'-_/, ]+", hxs.select('//h1[@id="prod-title"]/text()').extract()[0]))

        try:
            brand = hxs.select('//dt[contains(text(), "Brand")]'
                                   '/following-sibling::*[1]/text()').extract()[0].strip()
        except IndexError:
            brand = ''
        try:
            image_url = urljoin_rfc(base_url,
                                    hxs.select('//div[@id="prod-media-player"]'
                                               '//img/@src').extract()[0].strip())
        except IndexError:
            image_url = ''

        options = hxs.select('//div[@id="prod-multi-product-types"]')

        if options:
            products = options.select('.//div[@class="product-type"]')
            for product in products:
                opt_name = product.select('.//h3/text()').extract()[0].strip()
                try:
                    stock = product.select('//div[contains(@class, "mod-stock-availability")]'
                                           '//p/strong/text()').re(r'\d+')[0]
                except IndexError:
                    stock = 0

                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('sku', './/div[contains(@class, "mod-product-code")]/p/text()')
                loader.add_xpath('identifier', './/div[contains(@class, "mod-product-code")]/p/text()')
                loader.add_value('name', '%s %s' % (name, opt_name))
                loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[@class="last"]/a/text()')
                loader.add_value('image_url', image_url)
                loader.add_value('brand', brand)
                loader.add_value('url', response.url)
                loader.add_xpath('price', './/p[@class="price"]/strong/text()')
                loader.add_value('stock', stock)
                yield loader.load_item()
        else:
            price = ''.join(hxs.select('//div[@id="prod-price"]//strong/text()').extract()).split()

            try:
                stock = hxs.select('//div[contains(@class, "mod-stock-availability")]'
                                   '//p/strong/text()').re(r'\d+')[0]
            except IndexError:
                stock = 0

            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('sku', '//div[@id="prod-product-code"]/p/text()')
            loader.add_xpath('identifier', '//div[@id="prod-product-code"]/p/text()')
            loader.add_value('name', name)
            loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[@class="last"]/a/text()')
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('price', price)
            loader.add_value('stock', stock)
            yield loader.load_item()