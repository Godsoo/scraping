import csv
import os

import re
import urlparse
from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import datetime


def normalize_space(s):
    ''' Cleans up space/newline characters '''
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

HERE = os.path.abspath(os.path.dirname(__file__))

class EffortlessSkinSpider(BaseSpider):
    name = 'facethefuture-effortlessskin'
    allowed_domains = ['effortlessskin.com']
    start_urls = ['http://www.effortlessskin.com']

    def _start_requests(self):

        yield Request('http://www.effortlessskin.com/s-36-sun-protection.aspx', callback=self.parse_cat)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[@id="sf-nav"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        is_product = response.xpath('//*[@itemtype="http://schema.org/Product"]')
        if is_product:
            for item in self.parse_product(response):
                yield item

        try:
            entity_id = re.search("defaultEntityID = '(\d+)'", response.body).group(1)
        except:
            return
        if "defaultEntityType = 'Category'" in response.body:
            category_id = entity_id
            section_id = ''
        else:
            category_id = ''
            section_id = entity_id
        page = 0
        
        yield Request('http://www.effortlessskin.com/ISearch.aspx?PageNumber=%s&PageSize=48&PageSort=p.looks%%20desc&ColorFilter=&SizeFilter=&PriceFilter=&TypeFilter=&ManufacturerFilter=&CategoryFilter=%s&GenreFilter=&DistributorFilter=&VectorFilter=&SectionFilter=%s&LibraryFilter=&Filter=%%' % (page, category_id, section_id),
                meta={'category_id': category_id,
                        'section_id': section_id,
                        'category':hxs.select('//h1/text()').extract()[0]},
                callback=self.parse_page)

    def parse_page(self, response):
        hxs = HtmlXPathSelector(response)

        category_id = response.meta['category_id']
        section_id = response.meta['section_id']
        for page in hxs.select('//a[@class="PageLink"]/text()').extract():
            page = int(page.strip()) - 1
            yield Request('http://www.effortlessskin.com/ISearch.aspx?PageNumber=%s&PageSize=48&PageSort=p.looks%%20desc&ColorFilter=&SizeFilter=&PriceFilter=&TypeFilter=&ManufacturerFilter=&CategoryFilter=%s&GenreFilter=&DistributorFilter=&VectorFilter=&SectionFilter=%s&LibraryFilter=&Filter=%%' % (page, category_id, section_id),
                meta=response.meta, callback=self.parse_page)

        for productxs in hxs.select('//div[contains(@class,"product-grid")]'):
            product = Product()
            product['price'] = extract_price(''.join(productxs.select('.//span[@class="variantprice"]//text()|.//span[@class="SalePrice"]//text()').re(r'[\d.,]+')))
            if product['price'] == 0:
                product['stock'] = '0'
            else:
                product['stock'] = '1'
            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="pTitle"]/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            #yield self.fetch_product(request, self.add_shipping_cost(product))
            yield request

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        try: response.url.split('/')[-1].split('-')[1]
        except IndexError: return


        options = hxs.select('//div[@class="variantsInGridVariant"]')
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), selector=hxs)

                loader.add_value('url', response.url)
                identifier = option.select('.//input[contains(@id, "ProductID")]/@value').extract()
                if not identifier:
                    identifier = hxs.select('//input[@type="hidden" and @name="ProductID"]/@value').extract()
                identifier = identifier[0]
                option_id = option.select('.//input[contains(@id, "VariantID")]/@value').extract()[0]
                loader.add_value('identifier', identifier+'-'+option_id)
                loader.add_value('sku', response.url.split('/')[-1].split('-')[1])
                name = normalize_space(' '.join(hxs.select('//h1[@itemprop="name"]//text()').extract()))
                option_name = option.select('div[@class="vProdHolder"]/strong/text()').extract()
                option_name = option_name[0] if option_name else ''
                option_price = option.select('.//span[@itemprop="price"]/text()').extract()[0]
                loader.add_value('name', name + ' ' + option_name)
                loader.add_xpath('category', '//div[@id="breadcrumb"]/span/a/span/text()')
                loader.add_value('price', option_price)
                img = hxs.select('//img[@itemprop="image"]/@src').extract()
                if img:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

                loader.add_xpath('brand', '//span[@id="_bname"]/text()')
                yield loader.load_item()
        else:
            loader = ProductLoader(item=Product(), selector=hxs)

            loader.add_value('url', response.url)
            price = hxs.select('.//span[@itemprop="price"]/text()').extract()
            meta = response.meta
            if price:
                price = price[0]
            elif hxs.select('//div[contains(@class,"product-grid")]') and not meta.get('Retried', False):
                meta['retried'] = True
                yield Request(response.url, callback=self.parse_page, meta=meta)
            else:
                price = '0.00'
            loader.add_value('identifier', response.url.split('/')[-1].split('-')[1])
            # loader.add_value('sku', response.url.split('/')[-1][:-5])
            loader.add_value('sku', response.url.split('/')[-1].split('-')[1])
            loader.add_value('name', normalize_space(' '.join(hxs.select('//h1[@itemprop="name"]//text()').extract())))
            loader.add_xpath('category', '//div[@id="breadcrumb"]/span/a/span/text()')
            loader.add_value('price', price)
            # loader.add_value('category', response.meta.get('category'))
            img = hxs.select('//img[@itemprop="image"]/@src').extract()
            if img:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

            loader.add_xpath('brand', '//span[@id="_bname"]/text()')
            item = loader.load_item()
            radio_options = hxs.select('//span[@class="m-kit-radio"]')
            if radio_options:
                for i, option in enumerate(radio_options):
                    option_item = deepcopy(item)
                    option_identifier = hxs.select('//input[contains(@id, "ctl0'+str(i)+'_hdfKitItemId")]/@value').extract()[0]
                    option_item['identifier'] = option_item['identifier'] +'-'+ option_identifier
                    option_name = option.select('label/text()').extract()[0].split(' [')[0]
                    option_item['name'] = option_item['name'] +' '+ option_name
                    option_price = option.select('label/text()').re(r'Add (.*)]')
                    if option_price:
                        option_item['price'] = option_item['price'] + extract_price(option_price[0])
                    yield option_item
            else:
                yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        return item
