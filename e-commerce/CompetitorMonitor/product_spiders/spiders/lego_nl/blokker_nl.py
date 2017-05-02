from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import re


class BlokkerNlSpider(BaseSpider):
    name = 'blokker.nl'
    allowed_domains = ['blokker.nl']
    start_urls = ['http://www.blokker.nl/CategoryNavigationResultsView?pageSize=50&manufacturer=&searchType=&resultCatEntryType=&catalogId=11551&categoryId=&langId=-104&storeId=10156&sType=SimpleSearch&filterFacet=&metaData=KCh4YmxrZmZtdGludjoxMTA1MSkgT1IgKGFkc19mMjU1MDE6dHJ1ZSkp&beginIndex=0&catalogId=11551&contentBeginIndex=0&facet=&isHistory=false&langId=-104&maxPrice=&minPrice=&objectId=&orderBy=&orderByContent=&pageView=grid&productBeginIndex=0&requesttype=ajax&resultType=products&searchTerm=LEGO']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        page_size = 50
        current_page = response.meta.get('current_page', 0)
        items = hxs.select('//div[@class="product_info"]/div/a/@href').re(".*(http://.*)")

        for product in items:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        if items:
            current_page += 1
            next_url = add_or_replace_parameter(response.url, 'beginIndex', str(current_page * page_size))
            yield Request(next_url, meta={'current_page': current_page})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//h1[@itemprop="name"]/@id').re("product_name_([0-9]+)")

        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_value('price', hxs.select('//div[@id="productdetail"]/div/span/meta[@itemprop="price"]/@content').extract())

        sku = ' '.join(hxs.select('//h1//text()').extract())
        try:
            loader.add_value('sku', re.search('(\d+)', sku).groups()[0])
        except:
            self.log('Product without SKU: %s' % (response.url))
        loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[last()]/a/text()')

        img = hxs.select('//img[@id="productMainImage"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        
        if loader.get_output_value('price')<20:
            loader.add_value('shipping_cost', 2.99)

        yield loader.load_item()
