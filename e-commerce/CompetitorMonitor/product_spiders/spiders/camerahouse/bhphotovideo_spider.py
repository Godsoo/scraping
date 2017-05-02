import os

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import canonicalize_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

HOME = os.path.abspath(os.path.dirname(__file__))


class BhphotoVideoSpider(BigSiteMethodSpider):
    name = 'bhphotovideo.com'
    allowed_domains = ['bhphotovideo.com']

    website_id = 435939

    start_urls = ('http://www.bhphotovideo.com/c/browse/SiteMap/ci/13296/N/4294590034',)

    new_system = True
    old_system = True

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        cats = hxs.select(
                '//*[@id="tContent"]/div/div/div[@class="column"]'
                '/ul/li/a/@href').extract()
        if cats:
            for cat in cats:
                yield Request(
                        url=canonicalize_url(cat),
                        callback=self.parse_full)

        next_page = hxs.select(
                '//*[@id="bottompagination"]/div/a[@class="lnext"]/@href'
                ).extract()
        if next_page:
            if len(next_page)>1:
                yield Request(
                        url=canonicalize_url(next_page[1]),
                        callback=self.parse_full)
            else:
                yield Request(
                        url=canonicalize_url(next_page[0]),
                        callback=self.parse_full)

        products = hxs.select(
                '//div[@class="productBlock clearfix " '
                'or @class="productBlock clearfix topmrgn"]')
        if products:
            for product in products:
                brand = product.select(
                    'div/div/div[@class="brandTop"]/text()').extract()[0]
                title = product.select(
                    'div/div[@id="productTitle"]/h2/a/text()'
                ).extract()[0]
                name = ' '.join((brand, title))

                url = product.select('div/div[@id="productTitle"]/h2/a/@href').extract()[0]

                price = product.select(
                    'div[@id="productRight"]/ul/li[@class="price"]'
                    '/span[@class="value"]/text()').extract()
                if not price:
                    price = product.select(
                        'div[@id="productRight"]/ul'
                        '/li[@class="discountPrice"]'
                        '/span[@class="value"]/text()').extract()
                if not price:
                    price = product.select(
                        'div[@id="productRight"]/ul'
                        '/li[@class="map youPay"]'
                        '/span[@class="value"]/text()').extract()
                if not price:
                    price_label = product.select(
                        'div/ul/li/span[@class="label"]//text()'
                    ).extract()
                    if price_label and 'Savings' not in price_label[0]:
                        price = product.select(
                            'div/ul/li/span[@class="value"]/text()'
                        ).extract()
                if not price:
                    price = ''
                else:
                    price = price[0]

                if price:
                    loader = ProductLoader(item=Product(), selector=product)
                    loader.add_value('url', url)
                    loader.add_value('name', name)
                    loader.add_value('price', price)
                    yield loader.load_item()
                else:
                    # parse product page if price not found
                    yield Request(
                        url=url,
                        callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
 
        url = response.url
        name = " ".join(hxs.select("//div[@id='productHeadingCC']/h1/text()").extract()[0].split())
        price = hxs.select("//div[@id='productTop']//ul[@class='priceList ']/li"
                           "/span[@class='value']/text()").extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('url', url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        yield loader.load_item()
