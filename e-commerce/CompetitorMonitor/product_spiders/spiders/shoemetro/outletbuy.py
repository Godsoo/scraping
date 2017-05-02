import re

import logging

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from search_spider_class import SearchSpiderBase

class OutletBuySpider(SearchSpiderBase):
    name = 'outletbuy.com'
    allowed_domains = ['outletbuy.com','www.outletbuy.com']

    search_url = 'http://www.outletbuy.com/s.jsp?Search=%s'

    debug = True

    limit = 50

    def _create_search_url(self, name, color, size):
        query = name.replace(' ', '+')
        return self.search_url % query

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        table = hxs.select("//table[@class='search']/tr[.//span[@class='sectionName'][contains(text(), 'Matches to Style Names')]]")

        products = []
        for res in table.select(".//td[@class='searchright']/span[@class='null']"):
            name = "".join(res.select(".//text()").extract()).replace(":", "")
            if name.lower() in response.meta['name'] or response.meta['name'] in name.lower():
                url = res.select(".//a[last()]/@href").extract()
                url = urljoin_rfc(base_url, url[0])
                products.append(url)

        for url in products:
            meta = response.meta
            if products:
                meta['products'] = products
            yield Request(
                url,
                meta=response.meta,
                callback=self.parse_product,
                dont_filter=True
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product = hxs.select('//table[@class="buybox"]')

        if not product:
            return

        name = "".join(product.select('.//h1[@class="stylename"]/text()').extract()).strip()

        url = response.url

        color = None
        for color_title in product.select(".//select[@name='colors']/option/text()").extract():
            if color_title.strip().lower() == response.meta['color']:
                color = color_title

        size = None
        allowed_prefixes = ["Women's", "Men's"]
        for size_title in product.select(".//select[@name='sizes']/option/text()").extract():
            allowed_size = False
            for prefix in allowed_prefixes:
                if prefix in size_title:
                    allowed_size = True
                    break
            if not allowed_size:
                continue
            m = re.search(r'.*([\d.]+)$', size_title)
            if m:
                size_title = m.group(1)
                if size_title.lower() == response.meta['size']:
                    size = size_title

        price = product.select(".//span[@class='price']/span/text()").extract()
        if price:
            price = price[0].strip()
        else:
            logging.error("NO PRICE!!! %s, %s" % (url, name))

        if color is not None\
                and size is not None\
                and (name.lower() in response.meta['name'] or response.meta['name'] in name.lower()):
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('name', " ".join([name, color, "Size - " + size]))
            loader.add_value('url', url)
            loader.add_value('price', price)
            loader.add_value('sku', response.meta['sku'])
            yield loader.load_item()
        else:
            if 'products' in response.meta and response.meta['products']:
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
