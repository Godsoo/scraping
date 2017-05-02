# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin as urljoin_rfc
import demjson
import re
from eservicegroupitems import EServiceGroupMeta


class SlrhutCoUkSpider(BaseSpider):
    name = u'slrhut.co.uk'
    allowed_domains = ['slrhut.co.uk']
    start_urls = [
        'http://www.slrhut.co.uk'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="mainTopMenu"]/ul/li/a/@href').extract()[1:]:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)
        url = 'http://www.slrhut.co.uk/accessories/ID0C1/'
        yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//div[@class="itemPreviewContainer"]//div[@class="itemTitle"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url.replace("'", '')), callback=self.parse_product)
        # pagination
        for url in hxs.select('//p[@class="blockNavigationPages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        price = response.xpath('//script/text()').re('ecomm_totalvalue:(.*),')
        if not price:
            price = response.css('.itemPrice b::text').extract() or response.xpath('//span[@itemprop="price"]/text()').extract()
        brand = response.css('.brandImage ::attr(alt)').extract()
        id_text = response.xpath('//td[@class="itemActions"]/a/@onclick').extract()[0]
        match = re.search(r"slrhutAdd.*?ToCart\('(.*?)','(.*?)','(.*?)','.*?'\);",
                          id_text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            product_identifier = "{}_{}_{}".format(match.group(1), match.group(2), match.group(3))
        else:
            self.log('ERROR: Could not parse product identifier, URL: {}'.format(response.url))
            return

        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if not image_url:
            image_url = hxs.select('//td[@class="itemImage"]/img/@src').extract()
        product_name = response.xpath('//p[@itemprop="name"]/text()').extract()
        if not product_name:
            product_name = hxs.select('//p[@class="itemTitleHeader"]/a/text()').extract()
        product_name = product_name[0].strip()
        category = response.xpath('//p[@class="mainPageHeader"]//a/text()').extract()

        in_stock = response.xpath('//div[@class="itemContentAvailable"]//span/text()').extract()
        stock = True
        if in_stock and 'out of stock' in in_stock[0].lower():
            stock = False

        sku = response.xpath('//span[@itemprop="sku"]//text()').extract()
        if not sku:
            sku = hxs.select('//div[@class="itemContentMPN" and contains(., "SKU")]//text()').extract()
        sku = sku[-1] if sku else ''

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        if not stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        mpn = response.xpath('//div[@class="itemContentMPN" and contains(., "MPN")]//text()').extract()
        mpn = mpn[-1] if mpn else ''
        upc = response.xpath('//div[@class="itemContentMPN" and contains(., "UPC")]//text()').extract()
        upc = upc[-1] if upc else ''
        if mpn or upc:
            metadata = EServiceGroupMeta()
            if mpn:
                metadata['mpn'] = mpn
            if upc:
                metadata['upc'] = upc
            product['metadata'] = metadata
        yield product
