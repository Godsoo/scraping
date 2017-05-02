from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import re
from string import strip

from scrapy import log


class BartSmitComSpider(BaseSpider):
    name = 'bartsmit.com'
    allowed_domains = ['bartsmit.com']
    start_urls = ['http://www.bartsmit.com/nl/bsnl/speelgoed/lego/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        yield Request('http://www.bartsmit.com/CategoryNavigationResultsView?pageSize=50'
            '&manufacturer=&searchType=&resultCatEntryType=&catalogId=10051&categoryId=24049'
            '&langId=-104&storeId=10151&sType=SimpleSearch&filterFacet='
            '&metaData=KCh4YmxrZmZtdGludjoxMDU1MSkgT1IgKGFkc19mMjAwMDE6dHJ1ZSkp&beginIndex=0'
            '&catalogId=10051&contentBeginIndex=0&facet=&isHistory=false&langId=-104&maxPrice='
            '&minPrice=&objectId=&orderBy=&orderByContent=&pageView=grid&productBeginIndex=0'
            '&requesttype=ajax&resultType=products&searchTerm=&storeId=10151', callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[@class="product_info"]/div/a/@href').re(".*(http://.*)"):
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        next_page = hxs.select('//a[@id="WC_SearchBasedNavigationResults_pagination_link_right_categoryResults"]')
        if next_page:
            current_index = response.meta.get('current_index', 0)
            current_index += 50
            new_url = add_or_replace_parameter(response.url, 'beginIndex', str(current_index))
            new_url = add_or_replace_parameter(new_url, 'productBeginIndex', str(current_index))
            yield Request(new_url, callback=self.parse_list, meta={'current_index': current_index})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        
        identifier = hxs.select('//h1[@itemprop="name"]/@id').re("product_name_([0-9]+)")
        if identifier:
            identifier = identifier[0]
        else:
            log.msg('Product without identifier: ' + response.url)
            return

        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        price = hxs.select('//div[@id="productdetail"]/div/span/meta[@itemprop="price"]/@content').extract().pop()
        price = extract_price(price)

        loader.add_value('price', price)
        try:
            loader.add_value('sku', re.findall('(\d+)', loader.get_output_value('name'))[-1])
        except:
            pass
        loader.add_xpath('category', '//div[@id="widget_breadcrumb"]/ul/li[last() - 1]/a/text()')
        loader.add_xpath('image_url', '//a[@id="PD_image_zoom"]/@href')
        loader.add_value('brand', 'lego')
        if loader.get_output_value('identifier'):
            yield loader.load_item()
