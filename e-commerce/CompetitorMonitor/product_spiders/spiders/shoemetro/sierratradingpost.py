import logging

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from search_spider_class import SearchSpiderBase

class sierratradingpostSpider(SearchSpiderBase):
    name = 'sierratradingpost.com'
    allowed_domains = ['sierratradingpost.com','www.sierratradingpost.com']

    search_url = 'http://www.sierratradingpost.com/s~%s'

    search_results_parse_limit = 5

    def _create_search_url(self, name, color, size):
        query = name.replace(' ', '-').lower()
        return self.search_url % query

    def parse(self, response):
        logging.error("Searching for:")
        logging.error("Name: %s\nSize: %s\nColor: %s" % (response.meta['name'], response.meta['size'], response.meta['color']))
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//div[@id="products"]/div/div[contains(@class,"productThumbnailContainer")]//div[@class="productTitle"]/a/@href').extract()

        if not products:
            return
        url = urljoin_rfc(base_url, products.pop(0))

        meta = response.meta
        if products:
            meta['products'] = products
            meta['products_count'] = len(products) + 1

        yield Request(
            url,
            meta=meta,
            callback=self.parse_product,
            dont_filter=True
        )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = "".join(hxs.select("//div[@id='productDetails']//h1//text()").extract()).strip()
        url = response.url

        color = None
        for color_title in hxs.select("//select[@id='selectedProperty1']/option/text()").extract():
            if color_title.lower() == response.meta['color']:
                color = color_title

        size = None
        for size_title in hxs.select("//select[@id='selectedProperty2']/option/text()").extract():
            if size_title.lower() == response.meta['size']:
                size = size_title

        price = hxs.select("//span[@id='displayPrice']/text()").extract()
        if price:
            price = price[0].strip()
        else:
            logging.error("NO PRICE!!! %s, %s" % (url, name))

        if color is not None \
                and size is not None \
                and (name.lower() in response.meta['name'] or response.meta['name'] in name.lower())\
                and not 'apparelsave' in name:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('name', " ".join([name, color, "Size - " + size]))
            loader.add_value('url', url)
            loader.add_value('price', price)
            loader.add_value('sku', response.meta['sku'])
            yield loader.load_item()
        else:
            if 'products' in response.meta and response.meta['products'] and \
               (response.meta['products_count'] - len(response.meta['products']) < self.search_results_parse_limit):
                products = response.meta['products']
                url = urljoin_rfc(base_url, products.pop(0))
                meta = response.meta
                if products:
                    meta['products'] = products
                else:
                    del(meta['products'])

                yield Request(
                    url,
                    meta=meta,
                    callback=self.parse_product,
                    dont_filter=True
                )

