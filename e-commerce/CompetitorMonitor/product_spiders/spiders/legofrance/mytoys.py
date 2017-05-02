import csv
import os
import copy
import re
import urllib
import urlparse

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price_eu as extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class MyToysSpider(BaseSpider):
    name = 'legofrance-mytoys.fr'
    allowed_domains = ['mytoys.fr', 'mytoys.de']
    start_urls = ('http://www.mytoys.fr/LEGO/KID/fr-mt.to.br01.21/?sortrev=false&sort=name',
                  'http://www.mytoys.fr/LEGO/KID/fr-mt.lc.lc01.34/?sortrev=false&sort=name')
                  # 'http://www.mytoys.fr/LEGO-WEAR/KID/fr-mt.cw.br02.16/?sortrev=false&sort=name')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_urls = hxs.select(u'//span[@class="prodTitle"]//a/@href').extract()
        for url in product_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)
        
        next_page = hxs.select(u'//div[@class="paging"]//ul/li[last()]/a[img]/@href').extract()
        if not next_page:
            next_page = hxs.select(u'//li[@class="next"]/a[@class="next"]/@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])

            params =  {'sort': 'name', 'sortrev': 'false'}
            url_parts = list(urlparse.urlparse(url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urllib.urlencode(query)
            url = urlparse.urlunparse(url_parts)

            yield Request(url)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        identifier = response.url.split('/')[-1]

        name = hxs.select(u'//h1[@itemprop="name"]/text()')[0].extract().strip().replace('\t', '').replace('\n', ' ').replace(u'\xa0', u' ')



        sku = re.search('LEGO (?:duplo )?([\d]{3,6}) ', name)
        sku = sku.group(1) if sku else ''
        if not sku:
            sku = hxs.select(u'//div[@class="infoArea"]//p/text()').re(u'LEGO n\xb0 ([\d]+)')
            sku = sku[0] if sku else ''

        category = hxs.select(u'//div[@itemprop="breadcrumb" and @id="path"]//a[last()]/text()').extract()
        category = category[0] if category else ''
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_xpath('brand', u'//span[@itemprop="brand"]/text()')
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price = hxs.select(u'//span[@itemprop="price"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        loader.add_value('price', price)
        image = hxs.select(u'//img[@class="mainProductImage"]/@src').extract()
        image = image[0] if image else ''
        loader.add_value('image_url', image)
        if loader.get_output_value('brand') != 'LEGO WEAR':
            yield loader.load_item()
