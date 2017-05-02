import os
import shutil
from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from lecreusetitems import LeCreusetMeta

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class HouseOfFraserSpider(BaseSpider):
    name = 'lecreuset-houseoffraser.co.uk'
    allowed_domains = ['houseoffraser.co.uk', 'houseoffraserkitchenappliances.co.uk']
    start_urls = ['http://www.houseoffraser.co.uk/Le+Creuset+Home+Furniture/BRAND_LE%20CREUSET_05,default,sc.html#http://www.houseoffraser.co.uk/Le+Creuset+Home+Furniture/BRAND_LE%20CREUSET_05,default,sc.html&ajaxsearchrefinement']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//li[@class="product-list-element"]')
        if products:
            for product in products:
                url = product.select('a/@href').extract()[0]
                brand = ''.join(product.select('div//div[@class="product-description"]/a/h3/text()').extract()).strip()
                yield Request(url, callback=self.parse_product, meta={'brand':brand})

            next = hxs.select('//a[@class="pager nextPage"]/@href').extract()
            if next:
                yield Request(next[0])

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        products = hxs.select('//div[contains(@class, "item-details")]/div/header/h3/a/@href').extract()
        products += hxs.select('//div[contains(@class, "setProduct")]/div/h5/a/@href').extract()
        if products:
            for product in products:
                url = urljoin_rfc(get_base_url(response), product)
                yield Request(url, callback=self.parse_product, meta=meta)
            return

        category = hxs.select('//ol[contains(@class, "hof-breadcrumbs")]/li/a[@itemprop="breadcrumb"]/text()').extract()[-1]

        sku = hxs.select('//div[@class="product-code"]/text()').re(r'Product code:(.*)')[0].strip()
        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta['brand'])
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        image_url = hxs.select('//img[contains(@class, " featuredProductImage")]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        price = hxs.select('//div[@id="productDetailsRefinementBlock"]/div/span/p[@class="priceNow"]/span[@class="value"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="productPriceContainer"]/p[@class="price"]/text()').extract()

        loader.add_value('price', price[0])

        price_was = ' '.join(map(lambda x: x.strip(), hxs.select('//div[@id="productDetailsRefinementBlock"]//p[@class="priceWas"]/span//text()').extract())).strip()
        item = loader.load_item()
        metadata = LeCreusetMeta()
        metadata['promotion'] = price_was
        item['metadata'] = metadata

        yield item

        
