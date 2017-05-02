# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from itertools import product
import urlparse
from decimal import Decimal
import re
import urllib
import time
import json


from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class DreamtimebedsSpider(BaseSpider):
    name = 'dreamtimebeds'
    allowed_domains = ['dreamtimebeds.co.uk']
    start_urls = [
        'http://dreamtimebeds.co.uk/',
    ]
    
    handle_httpstatus_list = [411]
    
    price_xpath = "//div[@class='product-info']//span[@class='price-num'][2]/text()"
    select_xpath = "//div[contains(concat('',@id,''), 'product_options_update')]/div/div[not(contains(., 'Delivery'))]//select"
    in_store_xpath = "//div[@class='in_store_purchase_only']"
    name_xpath = "//h1[@class='mainbox-title']//text()"
    category_xpath = "//div[contains(concat('',@class,''), 'breadcrumbs')]//a[position() > 1]//text()"
    brand_xpath = "//div[@class='form-field'][contains(., 'Manufacturer')]/div//text()"
    img_xpath = "//div[@class='cm-image-wrap']//img/@src"

    price_regex = re.compile('\+\\xa3(\d+\.\d.)')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//li[@class='']//a/@href").extract()
        for category in categories:
            yield Request(
                urlparse.urljoin(response.url, category),
                callback=self.parse_category
            )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
        hxs = HtmlXPathSelector(response)

        # products
        for product_url in hxs.select("//div[@class='float-left product-item-image center']//a/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), product_url),
                callback=self.parse_product
            )

        # next page
        next_page_url_list = hxs.select("//span[@class='lowercase']/a/@href").extract()
        if next_page_url_list:
            yield Request(
                urlparse.urljoin(get_base_url(response), next_page_url_list[0]),
                callback=self.parse_category
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_data = {}
        product_data['name'] = hxs.select(self.name_xpath)[0].extract()
        product_data['url'] = response.url
        product_data['category'] = hxs.select(self.category_xpath)[0].extract()
        product_data['image_url'] = hxs.select(self.img_xpath).extract()
        if product_data['image_url']:
            product_data['image_url'] = urljoin_rfc(get_base_url(response), product_data['image_url'][0])
        product_data['brand'] = hxs.select(self.brand_xpath).extract()
        product_data['shipping_cost'] = '19.99'
        product_data['stock'] = '1'


        req_url = 'http://dreamtimebeds.co.uk/index.php?dispatch=products.options&'\
                  'changed_option[{product_id}]={option_id}&'\
                  'appearance[show_sku]=1&'\
                  'appearance[show_price_values]=1&'\
                  'appearance[show_old_price]=1&'\
                  'appearance[show_price_values]=1&'\
                  'appearance[show_price]=1&'\
                  'appearance[show_price_values]=1&'\
                  'appearance[show_list_discount]=1&'\
                  'appearance[show_discount_label]=1&'\
                  'appearance[show_price_values]=1&'\
                  'appearance[show_product_amount]=1&'\
                  'appearance[show_product_options]=1&'\
                  'appearance[details_page]=1&'\
                  'additional_info[info_type]=D&'\
                  'additional_info[get_icon]=1&'\
                  'additional_info[get_detailed]=1&'\
                  'additional_info[get_options]=1&'\
                  'additional_info[get_discounts]=1&'\
                  'additional_info[get_features]=&'\
                  'additional_info[get_extra]=&'\
                  'additional_info[get_categories]=&'\
                  'additional_info[get_taxed_prices]=1&'\
                  'additional_info[get_for_one_product]=1&'\
                  'appearance[show_qty]=1&'\
                  'appearance[show_list_buttons]=1&'\
                  'appearance[but_role]=big&'\
                  'appearance[separate_buttons]=1&'\
                  'appearance[quick_view]=&'\
                  'appearance[capture_options_vs_qty]=&'\
                  'product_data[{product_id}][amount]=1&'

        option_url = 'product_data[{product_id}][product_options][{select_id}]={option_value}'

        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.5',
                   'Cache-Control': 'no-cache',
                       'Connection': 'keep-alive',
                   'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'Host': 'dreamtimebeds.co.uk',
                   'Pragma': 'no-cache',
                   'Referer': response.url, #' http://dreamtimebeds.co.uk/new-world-windsor-divan-bed.html',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
                   'X-Requested-With': 'XMLHttpRequest'}
        form = hxs.select('//form[contains(@name,"product_form_")]')
        form_name = form.select('./@name')[0].extract()
        product_id = form_name.split('_')[-1]
        inputs = form.select('.//input')
        form_data = {'result_ids': 'product_images_{product_id}_update,sku_update_{product_id},old_price_update_{product_id},price_update_{product_id},line_discount_update_{product_id},discount_label_update_{product_id},product_amount_update_{product_id},product_options_update_{product_id},advanced_options_update_{product_id},qty_update_{product_id}'.format(product_id=product_id)}
        req = FormRequest(response.url, formdata=form_data, headers=headers, callback=self.parse_option, dont_filter=True)
        req.meta['req'] = req
        req.meta['product_id'] = product_id
        selects = hxs.select(self.select_xpath)
        if selects:
            first_select = [(elem.select('./@value')[0].extract(), elem.select('./text()')[0].extract()) for elem in selects[0].select('./option')]
            first_select_id = selects[0].select('./@id').re('_(\d+)$')[0]

            for value, text in first_select:
                select_name = selects[0].select('./@name')[0].extract()
                if value:
                    option_url = req_url.format(product_id=product_id, option_id=first_select_id) + select_name + '=' + value
                    option_req = req.replace(url=option_url)
                    option_req.meta['option_level'] = 1
                    option_req.meta['product'] = product_data
                    yield option_req
        else:
            loader = ProductLoader(item=Product(), response=response)

            price = hxs.select(self.price_xpath).extract()
            if price:
                price = extract_price(price[0])
                in_store = hxs.select(self.in_store_xpath)
                if in_store:
                    price += Decimal('19.99')

            identifier = hxs.select('//input[@type="hidden"]').re('product_data\[(\d+?)\]\[product_id\]')[0]

            loader.add_value('price', price)
            loader.add_value('url', response.url)
            loader.add_value('name', product_data['name'])

            loader.add_value('stock', '1')
            loader.add_xpath('category', self.category_xpath)
            loader.add_xpath('brand', self.brand_xpath)

            loader.add_value('shipping_cost', '19.99')

            loader.add_value('sku', identifier)
            loader.add_value('identifier', identifier)

            image_url = hxs.select(self.img_xpath).extract()

            if image_url:
                image_url = urlparse.urljoin(get_base_url(response), image_url[0])
            loader.add_value('image_url', image_url)
            yield loader.load_item()
                
    def parse_option(self, response):
        if response.status == 411:
            yield response.request
            return
        option_level = response.meta.get('option_level', 0)
        req = response.meta.get('req')
        product_id = response.meta.get('product_id')
        options = json.loads(response.body)
        hxs = HtmlXPathSelector(text=options['html']['product_options_update_' + product_id])
        selects = hxs.select('.//div[not(child::label[contains(text(),"Select Your Delivery")])]/select')
        if option_level < len(selects):
            select = [(elem.select('./@value')[0].extract(), elem.select('./text()')[0].extract()) for elem in selects[option_level].select('./option')]
            select_id = selects[option_level].select('./@id').re('_(\d+)$')[0]
            select_name = selects[option_level].select('./@name')[0].extract()
            for value, text in select:
                if value:
                    option_url = response.url + '&' + select_name + '=' + value
                    option_url = re.sub('(changed_option\[.*?\]=)\d+?&', '\g<1>{}&'.format(select_id), urllib.unquote(option_url))
                    option_req = req.replace(url=option_url, meta=response.meta)
                    option_req.meta['option_level'] = option_level + 1
                    yield option_req
        else:
            price_sel = HtmlXPathSelector(text=options['html']['price_update_' + product_id])
            stock_sel = HtmlXPathSelector(text=options['html']['product_amount_update_' + product_id])
            image_sel = HtmlXPathSelector(text=options['html']['product_images_{}_update'.format(product_id)])
            image_url = image_sel.select('.//a[contains(@class,"cm-image-previewer cm-previewer")]/@href').extract()
            product_data = response.meta.get('product')
            option_name = ' '.join(selects.select('./option[@selected]/text()').extract())
            identifier = product_id + '_' + '_'.join(selects.select('./option[@selected]/@value').extract())
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', clean_name('{} {}'.format(product_data['name'], option_name)))
            loader.add_value('category', product_data['category'])
            loader.add_value('brand', product_data['brand'])
            loader.add_value('url', product_data['url'])
            loader.add_value('shipping_cost', '19.99')
            price = price_sel.select('.//span[@class="price"]/span[@class="price-num"][2]/text()').extract()
            loader.add_value('price', price if price else '0.00')
            loader.add_value('stock', 1 if stock_sel.select('.//span[@class="in-stock"]') else 0)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            yield loader.load_item()

def clean_name(name):

    "Will remove the price from the name"
    return re.sub(r'\(.*?\)', '', name)
