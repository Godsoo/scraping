# -*- coding: utf-8 -*-
"""
Account: Red Hot Sunglasses
Name: redhotsunglasses-smartbuyglasses.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4915

Extract all products on site including any product options
Add the frame and lens to the product name http://screencast.com/t/Pw2fzI6f

"""

import os
import json

from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price



class ShadeStationSpider(BaseSpider):
    name = 'redhotsunglasses-shadestation.co.uk'
    allowed_domains = ['shadestation.co.uk']
    start_urls = ['https://www.shadestation.co.uk/']

    rotate_agent = True

    current_cookie = 0

    ajax_products_url = 'http://www.shadestation.co.uk/return_products.php'
    product_page_identifier_xpath = u'//div[label[text()="Shade Station code"]]/span/text()'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        page_no = response.meta.get('_page_', 1)

        headers = {'X-Request': 'JSON',
                   'x-requested-with': 'XMLHttpRequest',
                   'Accept': 'application/json'}
        params = {'limit': '28',
                  'orderby': 'mostpop',
                  'pageno': str(page_no)}
        req = FormRequest(self.ajax_products_url, formdata=params, 
                          headers=headers,
                          dont_filter=True,
                          meta={'_params_': params,
                                '_headers_': headers,
                                '_page_': page_no,
                                'cookiejar': self.current_cookie},
                          callback=self.parse_result)

        yield req


    def parse_result(self, response):
        base_url = get_base_url(response)

        data = json.loads(response.body)

        if data['currentpage'] < data['maxpages']:
            params = response.meta['_params_'].copy()
            params['pageno'] = str(data['currentpage'] + 1)
            yield FormRequest(self.ajax_products_url,
                              formdata=params,
                              headers=response.meta['_headers_'],
                              dont_filter=True,
                              meta={'_params_': params,
                                    '_headers_': response.meta['_headers_'],
                                    '_page_': params['pageno'],
                                    'cookiejar': self.current_cookie},
                              callback=self.parse_result)
        else:
            self.search_finished = True

        products = data['data']
        for product in products:
            product_url = urljoin_rfc(base_url, product['url'])
            product_url = add_or_replace_parameter(product_url, 'currency', 'GBP')
            yield Request(urljoin_rfc(base_url, product_url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = 'https://www.shadestation.co.uk/'

        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select(self.product_page_identifier_xpath).extract()
        if identifier:
            identifier = identifier[0].strip()
        else:
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 20:
                retry_no += 1
                yield Request(response.url,
                              meta={'dont_merge_cookies': True,
                                    'retry_no': retry_no},
                              dont_filter= True,
                              callback=self.parse_product)
            else:
                self.log('WARNING: possible blocking in => %s' % response.url)

            return

        sku = hxs.select(u'//span[@itemprop="productID"]/text()').extract()
        sku = sku[0] if sku else ''

        category = hxs.select(u'//div[@itemprop="breadcrumb"]/a/text()').extract()[1:]
        loader.add_value('identifier', identifier)

        name = hxs.select(u'//h1[@itemprop="name"]/text()').extract()[0]

        size = response.xpath('//select[@name="sizeSelector"]/option[@selected]/text()').extract()
        if size:
            name = name + ' ' + size[0].strip()

        extra_info = hxs.select('//div[@class="product_extra_info_area"]//text()').extract()
        if extra_info:
            extra_info = ' '.join(map(lambda x: x.strip(), extra_info)).strip()
            if 'lens' in extra_info.lower() or 'frame' in extra_info.lower():
                name = name + ' ' + extra_info

        colour = hxs.select('//li[contains(@class, "small_colour_selected")]/@rel').extract()
        if colour:
            if 'frame:' not in name.lower() and 'frame' in colour[0].lower():
                colour = colour[0].replace('<br/>', ' ').strip()
                name = name + ' ' + colour
            
        loader.add_value('name', name)

        #brand = hxs.select('//img[@id="product_logo"]/@src').re('images/(.*).svg')
        #brand = brand[0].replace('_', ' ') if brand else ''
        brand = ''
        if len(category) > 1:
            brand = category[1].split(' ')[:-1]
            brand = ' '.join(brand)
        loader.add_value('brand', brand)

        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        price = hxs.select(u'//div[@itemprop="price"]/text()').re('Our Price (.*)')
        if not price:
            price = hxs.select(u'//div[@itemprop="price"]/text()').extract()
        price = price[0] if price else '0.00'
        loader.add_value('price', price)
        image = hxs.select(u'//div[@id="product_image_crop"]/div/@imageurl').extract()
        image = image[0] if image else ''
        image = urljoin_rfc(base_url, image)
        loader.add_value('image_url', image)

        in_stock = response.xpath('//div[@itemprop="availability" and contains(text(), "In Stock")]')
        if in_stock:
            stock_level = response.xpath('//div[@class="furtherdetails"]/text()').re('\d+')
            stock = int(stock_level[0]) if stock_level else None
        else:
            stock = 0

        loader.add_value('stock', stock)


        yield loader.load_item()

