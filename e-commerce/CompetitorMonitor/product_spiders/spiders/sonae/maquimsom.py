# -*- coding: utf-8 -*-
"""
Original ticket: https://app.assembla.com/spaces/competitormonitor/tickets/5087
Extracted all products on site

"""
import datetime
import json
import os
import pandas as pd
from urlparse import urljoin as urljoin_rfc

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request
from scrapy.utils.url import url_query_parameter

from product_spiders.utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import DATA_DIR
from sonaeitems import SonaeMeta

class MaquimsomSpider(BaseSpider):
    name = 'sonae-maquimsom.pt'
    allowed_domains = ['maquimsom.pt']
    start_urls = ('http://www.maquimsom.pt',)

    def __init__(self, *args, **kwargs):
        super(MaquimsomSpider, self).__init__(*args, **kwargs)
        self.meta_df = None

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
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = response.xpath('//li[@class="lojas_menu_li"]/a/@href').extract()
        categories += response.xpath('//span[@class="cx_sub_cat"]/a/@href').extract()
        categories += response.xpath('//span[@class="MY_marcas_boxed"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//div[@class="ul_products_image"]/a/@href').extract()
        products += response.xpath('//div[@class="MY_newproducts_title"]/a/@href').extract()
        products += response.xpath('//td[@class="pr_list_name"]/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next_page = response.xpath('//a[@class="pageResults" and u[contains(text(), "Next")]]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        price = response.xpath(u'//tr[th[contains(text(), "Preço Campanha")]]/td/span/text()').extract()
        if not price:
            price = response.xpath(u'//tr[th[contains(text(), "Preço")]]/td/span/text()').extract()
        price = extract_price(price[0])
        product_loader.add_value('price', price)

        identifier = response.xpath('//input[@name="products_id"]/@value').extract()[0]
        product_loader.add_value('identifier', identifier)
        name = response.xpath('//div[@id="my_header"]//h2/text()').extract()[0].strip()
        product_loader.add_value('name', name)
        sku = response.xpath('//span[@class="smallText"]/text()').re('EAN\[(.*)\]')
        sku = sku[0] if sku else ''
        product_loader.add_value('sku', sku)
        image_url = response.xpath('//a[@rel="fancybox"]/img/@src').extract()
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url[0]))
        category = response.xpath('//div[@id="my_header"]//a/text()').extract()[-3:]
        product_loader.add_value('category', category)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('brand', '//div/@data-product-manufacture')

        metadata = SonaeMeta()
        promo = response.xpath('//div[@class="discount_block"]/span[@class="discount_block_text" and text()]')

        if self.meta_df is not None and not self.meta_df.empty and identifier in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier]
        else:
            prev_meta = {}
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

        stock = response.xpath('//div/@data-product-availability').extract()[0]
        if stock:
            stock = '1' == stock[0]
        else:
            stock = False
        if not stock:
            product_loader.add_value('stock', 0)

        product = product_loader.load_item()
        product['metadata'] = metadata
        yield product
