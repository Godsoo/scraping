# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import fix_spaces, extract_price2uk
import re, json
import itertools
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from w3lib.url import add_or_replace_parameter, url_query_parameter, url_query_cleaner

class BigBrandBedsCoUK(BaseSpider):
    name = "bigbrandbeds.co.uk"
    allowed_domains = ["bigbrandbeds.co.uk"]
    start_urls = ["http://www.bigbrandbeds.co.uk"]


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = response.css('div.jumbo-menu-categories a::attr(href)').extract()
        brand_urls = response.css('div.jumbo-menu-brands a::attr(href)').extract()
        for url in category_urls + brand_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        next_page_url = hxs.select('//ul[@class="pagination"]//li[last()]/a/@href').extract()
        if next_page_url:
            yield Request(urljoin(base_url, next_page_url[0]), callback=self.parse_category)

        product_urls = response.xpath('//h4[@class="media-heading"]/a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(selector=hxs, item=Product())

        brand = hxs.select('//section[contains(@class, "product-variations")]/div/div[2]/span/@data-img-attributes').extract()
        if not brand:
            brand = hxs.select('//u[./a/@href="#product-details"]/preceding-sibling::div[last()]//@data-img-attributes').extract()
        if brand:
            brand = re.findall(r'alt="(.*)"', brand[0])[0]
        sku = hxs.select('//h1[contains(@class, "product-title")]/following-sibling::p/text()').extract()
        sku = re.findall(r'\#(.*)', sku[0])
        image_url = hxs.select('//a[@class="thumbnail"]/@href').extract()
        if image_url:
            image_url = urljoin(base_url, image_url[0])
        price = hxs.select('//span[@class="price-price"]/text()').extract()
        if price:
            price = extract_price2uk(price[0])
            stock = 1
        else:
            price = 0
            stock = 0
        product_id = response.xpath('//input[@name="product_id"]/@value').extract_first()
        name = response.xpath('//h1[contains(@class, "product-title")]/text()').extract()[0]
        
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('brand', brand)
        loader.add_value('sku', sku)
        loader.add_value('image_url', image_url)
        loader.add_value('url', response.url)
        loader.add_value('identifier', product_id)
        loader.add_value('shipping_cost', 0)
        loader.add_value('stock', stock)
        product = loader.load_item()

        selects = response.css('.product-variations select')
        if not selects:
            yield product
            return
        selected_ids = response.xpath('//@data-selected-variable-ids').extract_first()
        selected_ids = json.loads(selected_ids)
        options = selects.pop(0).xpath('option[@value!=""]')
        get_sum_url = 'http://www.bigbrandbeds.co.uk/admin/controller/ProductVariations/getVariationData?productId=%s'
        get_menu_url = 'http://www.bigbrandbeds.co.uk/admin/controller/ProductVariations/getVariationsMenuData?productId=%s&optionId=%s'
        if selected_ids:
            form = {'variableIds[%s]' %var_id: str(selected_ids[var_id]) for var_id in selected_ids if selected_ids[var_id]}
        else:
            form = dict()
        if selects:
            url = get_menu_url %(product_id, selects.pop(0).xpath('@data-variations-menu').extract_first())
        else:
            url = get_sum_url %product_id
        options_name = ''
        for option in options:
            option_type_id = option.xpath('../@data-variations-menu').extract_first()
            if option_type_id:
                form['variableIds[%s]' %option_type_id] = option.xpath('@value').extract_first()
            option_name = option.xpath('text()').extract_first()
            request = FormRequest(url, formdata=form, 
                                method="GET",
                                callback=self.variant_sum, 
                                dont_filter=True)
            request.meta['product'] = Product(product)
            #request.meta['option_id'] = value
            request.meta['option_name'] = option_name
            request.meta['product_name'] = name
            request.meta['product_id'] = product_id
            if selects:
                request.meta['next_options'] = selects.xpath('@data-variations-menu').extract()[:]
            else:
                request.meta['next_options'] = []
            yield request
                
    def variant_sum(self, response):
        data = json.loads(response.body)
        options = data.get('variables')
        if options:
            option_type_id = url_query_parameter(response.url, 'optionId')
            for option in options:
                url = add_or_replace_parameter(response.url, 'variableIds[%s]' %option_type_id, option)
                meta=response.meta.copy()
                meta['product'] = Product(response.meta['product'])
                next_options = response.meta.get('next_options')[:]
                if next_options:
                    url = add_or_replace_parameter(url, 'optionId', next_options.pop(0))
                    meta['next_options'] = next_options[:]
                else:
                    url = ''.join(url.split('sMenu'))
                    url = url_query_cleaner(url, ('optionId',), remove=True)
                meta['option_name'] = response.meta['option_name'] + ' ' + options[option]
                yield Request(url, self.variant_sum, meta=meta)
            return
        product = Product(response.meta['product'])
        product['price'] = extract_price2uk(data['price'])
        product['name'] = fix_spaces(' '.join((response.meta['product_name'], response.meta['option_name'])))
        product['identifier'] = response.meta['product_id'] + '-' + data['id']
        yield product
           
        
