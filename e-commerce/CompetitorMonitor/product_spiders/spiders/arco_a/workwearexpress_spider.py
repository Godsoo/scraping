# -*- coding: utf-8 -*-
import re
from urlparse import urljoin as urljoin_rfc

# from scrapy.spider import BaseSpider
from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from decimal import Decimal


class WorkWeaErxpressSpider(PrimarySpider):
    name = 'arco-a-workwearexpress.com'
    allowed_domains = ['workwearexpress.com']
    start_urls = ('http://www.workwearexpress.com/',)

    csv_file = 'workwearexpress_crawl.csv'
    custom_settings = {'COOKIES_ENABLED': False}
    download_delay = 0.4

    def proxy_service_check_response(self, response):
        return response.status == 400
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@id="top_nav"]/li//a')

        for category in categories:
            url = category.select('@href').extract()[0]
            name = category.select('text()').extract()
            if name:
		request = Request(urljoin_rfc(base_url, url), callback=self.parse_product_list, meta={'category':name[0]}, dont_filter=True)
		yield request

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        products_urls = hxs.select('//div[@class="brok_item"]/a/@href').extract()
        for url in products_urls:
            meta = response.meta.copy()
            #meta['dont_redirect'] = True
            yield Request(url, callback=self.parse_product, meta=meta)

        next_page = hxs.select('//li[contains(@class, "next")]/a/@href').extract()
        if next_page:
            yield Request(next_page[0], callback=self.parse_product_list, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        main_name = hxs.select('//div[@id="prodpage_title"]/h1/text()').extract()[0]
        image_url = hxs.select('//img[@id="productpage_main_image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])

        sizes = response.xpath('//div[@id="product_grid"]/table//th[not(contains(., "Enter Quantity"))]')[1:]
        sizes = response.xpath('//select[@id="size_select"]/option[not(contains(., "Select"))]')

        color_rows = response.xpath('//div[@id="product_grid"]/table//tr')[1:]

        if not sizes and not color_rows:
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                meta = response.meta.copy()
                meta['retry_no'] = retry_no + 1
                yield Request(response.url, callback=self.parse_product, meta=meta, dont_filter=True)
            return

        root_id = hxs.select('//input[@name="root_product_id"]/@value').extract()[0]

        for row in color_rows:
            color_id = row.xpath('@data-colourid').extract_first()
            color = response.xpath('//input[@name="colour_radio"][@value="%s"]/@title' %color_id).extract_first()
            for i, size in enumerate(sizes):
                size_name = ' '.join(size.select('.//text()').extract()).strip().replace(',', '').replace('"','')
                input_sel = row.select('td[%s]/input' % (i + 2))
                if True:
                    identifier = '%s-%s-%s' % (root_id, size_name, color)
                    identifier = identifier.lower()

                    loader = ProductLoader(item=Product(), selector=input_sel)
                    loader.add_value('identifier', identifier)
                    loader.add_xpath('sku', '//span[@itemprop="sku"]/text()')
                    loader.add_value('name', main_name + ' Size: %s, Color: %s' % (size_name, color))
                    loader.add_xpath('price', '//div[@class="price_breaks"]/ul/li/span/text()')
                    loader.add_value('category', response.meta['category'])
                    loader.add_xpath('brand', '//div[@id="prodpage_title"]/img/@alt')
                    loader.add_value('image_url', image_url)
                    loader.add_value('url', response.url)

                    price = loader.get_output_value('price')
                    if price < Decimal(100):
                        loader.add_value('shipping_cost', 4.95)
                    else:
                        loader.add_value('shipping_cost', 0)

                    if not price:
                        loader.add_value('stock', 0)

                    yield loader.load_item()
