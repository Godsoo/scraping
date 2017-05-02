# from csv import DictReader
# from petsafeconfig import SKU_CSV_FILENAME
import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging


class PetsafeNetSpider(BaseSpider):
    name = 'petsafe.net'
    allowed_domains = ['petsafe.net']
    start_urls = (
        'http://www.petsafe.net/products',
    )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories
        for url in hxs.select("//ul[@id='menuElem']//li/a/@href").extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        # products
        for product in hxs.select("//ul[@id='categoryproductWrapper']//div[@class='productWrapper']"):
            if product.select("div[@class='catContent']/div[@class='modelNumber']").extract():
                url = product.select("header/a/@href").extract()
                if not url:
                    logging.error('ERROR!! NO URL!! %s' % (response.url, ))
                    continue
                url = url[0].strip()
                url = urljoin_rfc(get_base_url(response), url)

                sku = product.select("div[@class='catContent']/div[@class='modelNumber']/text()").extract()
                if not sku:
                    yield Request(url, callback=self.parseProduct)
                    continue
                sku = sku[0].replace("SKU:", "").strip()

                name = product.select("header/a/text()").extract()
                if not name:
                    logging.error('ERROR!! NO NAME!! %s "%s"' % (response.url, sku))
                    continue
                name = name[0].strip()

                price = product.select("div[@class='catContent']/div[@class='descPrice']/text()").extract()
                if not price:
                    logging.error('ERROR!! NO PRICE!! %s "%s"' % (response.url, sku))
                    continue
                price = price[0].strip()

                product = Product()
                loader = ProductLoader(item=product, response=response, selector=hxs)
                loader.add_value('identifier', sku)
                loader.add_value('url', url)
                loader.add_value('name', name)
                loader.add_value('price', price)

                loader.add_value('sku', sku)

                yield loader.load_item()

    def parse_options(self, options):
        if not options:
            return
        for i in xrange(0, len(options)):
            option = options[i]
            if option['Link']:
                price = option['Price']
                sku = option['SKU']
                yield option['Link'], False, price, sku
            else:
                for url, opt, price, sku in self.parse_options(option['Options']):
                    if opt is not False:
                        opt = str(i + 1) + "," + opt
                    else:
                        opt = str(i + 1)
                    yield url, opt, price, sku

    def get_options(self, hxs):
        raw_options = hxs.select("//script").re("productOptions = eval([^;]*);")
        if raw_options:
            raw_options = raw_options[0]
            options = json.loads(re.search(r"'({\"Options[^']*)'", raw_options).group(1))
            for url, opts, price, sku in self.parse_options(options['Options']):
                url = url + "?opt=" + opts
                logging.error("OPTIONS URLS: %s" % url)
                yield url, price, sku
            # for url in re.findall(r'"Link":"([^"]*)",', raw_options):
            #     yield url

    def parseProduct(self, response):
        hxs = HtmlXPathSelector(response)

        sku = hxs.select("//ul[@class='buying']//div[@class='sku-text']/text()").extract()
        if not sku:
            logging.error('ERROR!! NO SKU!! %s' % (response.url, ))
        else:
            sku = sku[0].replace("SKU:", "").strip()

        name = hxs.select("//div[@class='prodDescWrapper']/h1/text()").extract()
        if not name:
            logging.error('ERROR!! NO NAME!! %s' % (response.url, ))
            return
        name = name[0].strip()

        price = hxs.select("//ul[@class='buying']//div[@class='price-text']/text()").extract()
        if not price:
            logging.error('ERROR!! NO PRICE!! %s' % (response.url, ))
        else:
            price = price[0].strip()

        if not sku or not price:
            logging.error('ERROR!! NO PRICE OR SKU!! %s' % (response.url, ))
            # parse options
            try:
                for url, price, sku in self.get_options(hxs):
                    url = urljoin_rfc(get_base_url(response), url)
                    yield Request(url, callback=self.parseProductOption, meta={'price': price, 'sku': sku})
            except Exception:
                pass

            return

        if not sku:
            logging.error('ERROR!! NO SKU!! %s' % (response.url, ))
            return

        product = Product()
        loader = ProductLoader(item=product, response=response, selector=hxs)
        loader.add_value('identifier', sku)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)

        loader.add_value('sku', sku)

        yield loader.load_item()

    def parseProductOption(self, response):
        hxs = HtmlXPathSelector(response)
        # parse title for SKU
        title = hxs.select("//title/text()").extract()[0]
        name = title.split("|")[0]

        sku = response.meta['sku']
        price = response.meta['price']

        product = Product()
        loader = ProductLoader(item=product, response=response, selector=hxs)
        loader.add_value('identifier', sku)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)

        loader.add_value('sku', sku)

        yield loader.load_item()
