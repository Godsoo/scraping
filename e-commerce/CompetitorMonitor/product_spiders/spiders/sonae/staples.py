import datetime
import json
import os
import re
import csv
from decimal import Decimal

import pandas as pd
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
from product_spiders.config import DATA_DIR
from sonaeitems import SonaeMeta


class StaplesSpider(BaseSpider):
    name = 'sonae-staples.pt'
    allowed_domains = ['staples.pt']
    start_urls = ['http://www.staples.pt']

    def __init__(self, *args, **kwargs):
        super(StaplesSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.meta_df = None
        self.old_crawl_filename = ''
        self.old_urls = []

    def spider_idle(self, spider):
        while self.old_urls:
            url = self.old_urls.pop()
            request = Request(url, callback=self.parse_product)
            self._crawler.engine.crawl(request, self)

    def start_requests(self):
        if self.meta_df is None and hasattr(self, 'prev_crawl_id'):
            meta_filename = os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % self.prev_crawl_id)
            if os.path.exists(meta_filename):
                with open(meta_filename) as f:
                    self.meta_df = pd.DataFrame(columns=['identifier', 'promo_start', 'promo_end'], dtype=pd.np.str)
                    for i, line in enumerate(f):
                        p = json.loads(line.strip())
                        self.meta_df.loc[i] = {'identifier': p['identifier'], 'promo_start': p['metadata'].get('promo_start'),
                                               'promo_end': p['metadata'].get('promo_end')}
                    self.meta_df.set_index('identifier', drop=False, inplace=True)
        elif not hasattr(self, 'prev_crawl_id'):
            self.log('prev_crawl_id attr not found')
        if hasattr(self, 'prev_crawl_id'):
            self.old_crawl_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            with open(self.old_crawl_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['url'] not in self.old_urls:
                        self.old_urls.append(row['url'])

        cookies = {'b_fn': 'RecentSKUs=&RecentSearchText=&runa_uot=0&SearchAB=2&SearchUIVersion=2&includevat=1'}
        for url in self.start_urls:
            yield Request(url, cookies=cookies)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@id="wrapPrimaryNav"]/div[contains(@class,"PrimarySubnav")]//a[contains(@class,"secondLevel")]/@href').extract()
        categories += hxs.select('//div[@class="primaryNav"]/span/a[not(@href="")]/@href').extract()

        subcategories = hxs.select('//div[contains(@class,"supCatFigures")]//a/@href').extract()
        subcategories += hxs.select('//a[@class="desc3"]/@href').extract()
        subcategories += hxs.select('//div[@class="shopByBrandList"]//li/a/@href').extract()

        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        for url in subcategories:
            yield Request(urljoin_rfc(base_url, url))

        for url in hxs.select('//a[@id="ShowMoreResults"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url))

        products = hxs.select('//div[@id="searchItem"]//h3[@id="skuName"]/a/@href').extract()
        products += hxs.select('//div[@id="ITNarrowBrandContent"]//li/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)


    def parse_product(self, response):
        if response.url in self.old_urls:
            self.old_urls.remove(response.url)

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@id="searchItem"]//h3[@id="skuName"]/a/@href').extract()
        if products:
            for url in products:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)



        loader = ProductLoader(item=Product(), response=response)

        identifier = hxs.select('//div[@itemprop="productID"]/text()').extract()
        identifier = identifier[0].strip().split(' ')[-1].strip() if identifier else ''
        sku = identifier

        stock = hxs.select("//link[@itemprop='availability']/@href").extract()
        stock = stock[0] if stock else ''
        stock = 0 if 'OutOfStock' in stock else 1

        name = hxs.select("//h1[@itemprop='name']/text()").extract()
        name = name[0] if name else ''

        if not name:
            return

        categories = hxs.select('//div[@id="skuBreadCrumbs"]//span[@itemprop="title"]/text()').extract()
        categories = list(set(categories))

        image_url = hxs.select('//img[@id="SkuPageMainImg"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''

        brand = re.findall(re.compile("brandName\":\[\"(.+?)\"\]"), response.body)
        brand = brand[0] if brand else ''

        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        price = price[0].replace('.', '').replace(',', '.').strip() if price else '0.00'

        loader.add_value('price', price)

        price = loader.get_output_value('price')
        if price:
            price = Decimal(price)
            if price <= 48.99:
                loader.add_value('shipping_cost', '3.00')

        loader.add_value('stock', stock)
        loader.add_value('brand', brand.decode('utf-8'))
        loader.add_value('url', response.url)
        loader.add_value('image_url', image_url)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('name', name)
        for category in categories:
            loader.add_value('category', category)

        product = loader.load_item()

        metadata = SonaeMeta()
        promotional_price = hxs.select('//div[@id="SkuSaveStory"]//span[contains(@class, "strike") '
                                       'and contains(@class, "darkGray")]/text()') \
            .re(r'[\d,.]+')
        if promotional_price:
            metadata['promotion_price'] = promotional_price[0].replace('.', '').replace(',', '.')

        if self.meta_df is not None and not self.meta_df.empty and identifier in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier]
        else:
            prev_meta = {}
        promo = promotional_price
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        metadata['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            metadata['promo_start'] = promo_start if promo_start and not promo_end else today
            metadata['promo_end'] = ''
        else:
            if promo_start:
                metadata['promo_start'] = promo_start
                metadata['promo_end'] = today if not promo_end else promo_end

        metadata['delivery_24'] = 'Yes'
        product['metadata'] = metadata
        yield product
