import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import csv

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class RVPartsCenterSpider(BaseSpider):
    name = 'rvpartscenter_americanrv.com'

    allowed_domains = ['www.rvpartsscenter.com']
    start_urls = ('http://www.rvpartscenter.com/',)
    retry_urls = {}
    user_agent = 'Opera/9.80 (Windows NT 6.1; U; es-ES) Presto/2.9.181 Version/12.00'

    def start_requests(self):
        existing_products = []
        with open(os.path.join(HERE, 'rvpartsproducts.csv')) as f:
            reader = csv.reader(f)
            reader.next()
            for row in reader:
                existing_products.append(row[0])
                meta = dict()
                meta['search_q'] = meta['sku'] = meta['mfrgid'] = row[0]
                yield Request(row[1], meta=meta, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        special_price_url = hxs.select("//td[@class='tdcf10bk']/a/@href").extract()
        if special_price_url:
            special_price_url = special_price_url[0]
            special_price_url = urljoin_rfc(get_base_url(response), special_price_url)

            request = Request(url=special_price_url, callback=self.parse_product)
            request.meta['sku'] = response.meta['sku']
            request.meta['mfrgid'] = response.meta['mfrgid']
            request.meta['search_q'] = response.meta['search_q']
            yield request
            return

        product_loader = ProductLoader(item=Product(), response=response)

        name = hxs.select("//h1/font/b/text()").extract()
        price = hxs.select("//font[@color='#990000']/b/text()").extract()
        if not name or not price:
            retry_count = self.retry_urls.get(response.url, 0)
            retry_count += 1
            if retry_count > 100:
                self.log("ERROR MAX retry count reached (100), giving up...")
                return
            else:
                self.log("ERROR parsing HTML, adding to retry queue (#{})".format(retry_count))
                self.retry_urls[response.url] = retry_count
                request = Request(url=response.url, callback=self.parse_product, dont_filter=True)
                request.meta['sku'] = response.meta['sku']
                request.meta['mfrgid'] = response.meta['mfrgid']
                request.meta['search_q'] = response.meta['search_q']
                yield request
                return
        else:
            product_loader.add_value('name', name[0])
            product_loader.add_value('price', price[0])
            product_loader.add_value('url', response.url)
            product_loader.add_value('sku', response.meta['sku'].lower())
            product_loader.add_xpath('identifier', '//form/input[@name="PID"]/@value')
            yield product_loader.load_item()