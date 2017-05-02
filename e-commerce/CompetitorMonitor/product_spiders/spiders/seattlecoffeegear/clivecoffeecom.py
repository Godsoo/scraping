import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
import re


class ClivecoffeeComSpider(BaseSpider):
    name = 'clivecoffee.com'
    allowed_domains = ['clivecoffee.com']
    start_urls = (
        'http://www.clivecoffee.com/SMAP.html',
#         'http://www.clivecoffee.com/category/view_all_items.html',
#         'http://www.clivecoffee.com/category/brands_frieling.html',
#         'http://www.clivecoffee.com/category/coffeemaker_accessories.html',
#         'http://www.clivecoffee.com/category/immersion_brew.html',
#         'http://www.clivecoffee.com/category/literature.html',
#         'http://www.clivecoffee.com/category/brand_clive_coffee.html',
#         'http://www.clivecoffee.com/category/thermal_carafe.html',
#         'http://www.clivecoffee.com/category/coffee_cups.html',
#         'http://www.clivecoffee.com/category/kettles.html',
    )

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//ul[@id="sitemap"]//a')
        categories += hxs.select("//div[@id='side-nav']/ul/li//a")
        for cat in categories:
            category = cat.select('text()').extract()[0].strip()
            url = cat.select('@href').extract()[0]
            url = urljoin_rfc(base_url, url)
            meta = response.meta.copy()
            meta['category'] = category
            yield Request(url, meta=meta)

        # products list
        products = hxs.select('//ul[@id="category-row-items"]/li')
        if not products:
            print "ERROR!! NO PRODUCTS!! %s " % response.url
            logging.error("ERROR!! NO PRODUCTS!! %s " % response.url)
        for product_el in products:
            name = product_el.select('.//div[@class="item-name"]/h2/a/text()').extract()
            if not name:
                print "ERROR!! NO NAME!! %s " % response.url
                logging.error("ERROR!! NO NAME!! %s " % response.url)
                continue
            name = name[0]

            url = product_el.select('.//div[@class="item-name"]/h2/a/@href').extract()
            if not url:
                print "ERROR!! NO URL!! %s" % response.url
                logging.error("ERROR!! NO URL!! %s " % response.url)
                continue
            url = urljoin_rfc(base_url, url[0])

            price = product_el.select('.//div[@class="item-total"]/text()').extract()
            if not price:
                print "ERROR!! NO PRICE!! %s" % response.url
                logging.error("ERROR!! NO PRICE!! %s " % response.url)
                continue
            price = price[0]

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('category', response.meta.get('category', ''))

            yield Request(url, callback=self.parse_product, meta={'loader': loader})

        if not products and '/product/' in response.url:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if 'loader' in response.meta:
            loader = response.meta['loader']
        else:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', response.url)
            loader.add_xpath('name', '//*[@itemprop="name"]/text()')
            loader.add_xpath('price', '//*[@itemprop="price"]/@content')
            loader.add_value('category', response.meta.get('category', ''))

        try:
            identifier = hxs.select('//input[@type="hidden" and @name="Product_Code"]/@value')[0].extract()
        except:
            identifier = ''

        if not identifier:
            identifier = re.search(r'product/(.*).html$', response.url).group(1)

        loader.add_value('identifier', identifier)

        image_url = ''
        line_no = None

        for i, line in enumerate(response.body.split('\n')):
            if '"image_data":' in line:
                line_no = i
                break

        if line_no is not None:
            image_url = response.body.split('\n')[line_no + 2].replace('\\', '')[1:-2]

        if image_url:
            image_url = urljoin_rfc(base_url, image_url)
            loader.add_value('image_url', image_url)

        out_of_stock = hxs.select('//p[@class="notifications"]//strong[contains(text(),"On backorder")]')
        if out_of_stock:
            loader.add_value('stock', 0)

        try:
            shipping_cost = '0.00' if float(loader.get_output_value('price')) >= 75.00 else '5.00'
            loader.add_value('shipping_cost', shipping_cost)
        except:
            return


        yield loader.load_item()
