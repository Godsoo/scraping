import re
import os
import csv
import shutil

from datetime import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import (Product,
                                   ProductLoaderWithNameStrip as ProductLoader)
from lib.schema import SpiderSchema
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

HERE = os.path.abspath(os.path.dirname(__file__))


class ArgosCoUKSpider(BaseSpider):
    name = 'legouk-argos.co.uk'
    allowed_domains = ['argos.co.uk']
    start_urls = ('http://www.argos.co.uk/static/Browse/ID72/33014616/c_1/1|category_root|Toys|33006252/c_2/2|33006252|LEGO+and+construction+toys|33006903/c_3/3|cat_33006903|LEGO|33014616.htm',)

    def __init__(self, *args, **kwargs):
        super(ArgosCoUKSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._filename = 'argos_products.csv'

        if os.path.exists(os.path.join(HERE, self._filename)):
            shutil.copy(os.path.join(HERE, self._filename),
                        os.path.join(HERE, self._filename + '.bak'))

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, self._filename))

    def start_requests(self):

        if os.path.exists(os.path.join(HERE, self._filename)):
            with open(os.path.join(HERE, self._filename)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'], self.parse_product)

        for url in self.start_urls:
            yield Request(url)

    def parse_product(self, response):
        pdata = SpiderSchema(response).get_product()
        hxs = HtmlXPathSelector(response)

        url = response.url
        l = ProductLoader(item=Product(), response=response)
        
        name = pdata['name']

        l.add_value('name', pdata['name'])

        sku = re.search('(\d{3,})\.*$', name)
        if not sku:
            self.log("ERROR! SKU! %s %s" % (url, name))
            # return
        else:
            l.add_value('sku', sku.group(1))

        l.add_value('category', SpiderSchema(response).get_category())

        product_image = response.css('li.active a img::attr(src)').extract_first()
        if product_image:
            l.add_value('image_url', response.urljoin(product_image))

        l.add_value('url', url)
        l.add_value('price', pdata['offers']['properties']['price'])
        l.add_value('brand', 'Lego')
        l.add_xpath('identifier', u'//form/input[@name="productId"]/@value')
        yield l.load_item()

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # parse pages
        pages = hxs.select("//div[contains(@class, 'pagination')]//a[@class='button']/@href").extract()
        for page in pages:
            yield Request(page)

        # parse products
        items = hxs.select("//div[@id='products']/ul/li[contains(@class, 'item')]/dl")
        for item in items:
            url = item.select('dt[@class="title"]/a/@href').extract()
            if not url:
                self.log("ERROR! NO URL! URL: %s." % (response.url,))
                continue
            url = urljoin_rfc(base_url, url[0])

            yield Request(url, callback=self.parse_product)
