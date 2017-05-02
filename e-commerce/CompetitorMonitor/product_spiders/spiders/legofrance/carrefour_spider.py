import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

class CarrefourSpider(BaseSpider):
    name = 'legofrance-carrefour.fr'
    allowed_domains = ['carrefour.fr']
    start_urls = ('http://online.carrefour.fr/jouets-jeux/jouets-garcon/lego_m3296_frfr.html',
		  'http://online.carrefour.fr/jouets-jeux/jeux-de-construction/lego_m22611-frfr.html')

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        try:
            product_urls = hxs.select('//td[@class="prd"]/div/a/@href').extract()
        except TypeError:
            log.msg('End of pagination')
            return

        for url in product_urls:
            yield Request(url, callback=self.parse_product)

        if product_urls:
            paging_url = 'http://online.carrefour.fr/jouets-jeux/jeux-de-construction/lego_ism22611-xx-xx-xx-xx-relevance-%s_12-frfr.html?p=1'
            page = response.meta.get('page', 1) + 1
            yield Request(paging_url % page, meta={'page': page})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        l = ProductLoader(item=Product(), response=response)
        identifier = ''
        sku = ''
        split_name = hxs.select('//h1[@class="page-title"]/span/text()').extract()[0].split(' - ')
        for item in split_name:
            if item.isdigit():
                sku = item

        if not sku:
            sku = ''

        identifier = re.search(r'_a(\d+)_', response.url).groups()[0]

        category = hxs.select('//div[@id="breadcrumb"]/span/a/span/text()').extract()[-1].strip()
        l.add_value('identifier', identifier)
        l.add_xpath('name', '//h1[@class="page-title"]/span/text()')
        l.add_xpath('brand', '//h1[@class="page-title"]/a/text()')
        l.add_value('category', category)
        l.add_value('sku', sku)
        l.add_value('url', response.url)
        price = hxs.select('//*[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//p[@class="prd-amount"]/strong[@class="prd-price"]/text()').extract()
        price = price[0].replace(',', '.') if price else 0
        l.add_value('price', price)
        image = hxs.select('//div[@class="box-footer"]/ul/li/a/@href').extract()
        image = image[0] if image else hxs.select('//img[@class="photo"]/@src').extract()[0]
        l.add_value('image_url', image)
        yield l.load_item()
