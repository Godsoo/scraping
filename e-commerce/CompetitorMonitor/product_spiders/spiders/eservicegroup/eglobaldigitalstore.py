import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from decimal import Decimal

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class EGlobalDigitalStoreSpider(BaseSpider):
    name = u'eglobaldigitalstore.co.uk'
    allowed_domains = [u'eglobaldigitalstore.co.uk']
    start_urls = (u'http://www.eglobaldigitalstore.co.uk/?type=extended&search_performed=Y&match=any&q=&pname=N&pname=Y&cid=0&pcode=&price_from=&price_to=&weight_from=&weight_to=&dispatch%5Bproducts.search%5D=Search&sort_by=name&sort_order=asc',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = []
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category.select(u'./@href')[0].extract())
            url += u'?sort_by=price&sort_order=desc'
            yield Request(url, meta={'category': category.select(u'./text()')[0].extract()})

        pages = hxs.select(u'//div[@class="pagination-container"]//a[@name="pagination"]/@href').extract()
        for url in pages:
            url = urljoin_rfc(get_base_url(response), url.replace('`?', '?'))
            yield Request(url, meta=response.meta)

        products = hxs.select(u'//td[@class="product-description"]/a/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select(u'//h1[@class="mainbox-title"]/text()')[0].extract()
        loader.add_value('name', name)

        loader.add_value('url', response.url)

        price = hxs.select(u'//div[@id="product_info"]//span[@class="price"]/span[@class="price" and @id]/text()')
        if not price:
            price = hxs.select(u'//*[@itemprop="price"]/span[@class="price" and @id]/text()')
        price = price[0].extract().replace(',', '')
        loader.add_value('price', price)

        image_url = hxs.select(u'//a[contains(text(),"View larger image")]/@href')
        if image_url:
            image_url = urljoin_rfc(get_base_url(response), image_url[0].extract())
            loader.add_value('image_url', image_url)
        category = hxs.select(u'//div[@class="breadcrumbs"]/a[1]/following-sibling::a[1]/text()').extract()
        if category:
            loader.add_value('category', category[0])
        sku = hxs.select(u'//div[@class="product-main-info" or @id="product_info"]//p[@class="sku"]//span[starts-with(@id,"product_code")]/text()')
        if sku and sku[0].extract().lower() != 'n/a':
            sku = sku[0].extract().lower()
            loader.add_value('sku', sku)

        loader.add_xpath('identifier', '//input[contains(@name, "product_id")]/@value')

        options = hxs.select(u'//div[starts-with(@id,"opt_")]//select/option')

        select_name = hxs.select(u'//div[starts-with(@id,"opt_")]//select/@name').extract()

        if len(options) == 1:
            formdata = {'additional_info[get_detailed]': '1',
                        'additional_info[get_discounts]': '1',
                        'additional_info[get_features]': '',
                        'additional_info[get_icon]': '1',
                        'additional_info[get_options]': '1',
                        'additional_info[info_type]': 'D',
                        'appearance[but_role]': 'action',
                        'appearance[capture_options_vs_qty]': '',
                        'appearance[details_page]': '1',
                        'appearance[separate_buttons]': '',
                        'appearance[show_add_to_cart]': '1',
                        'appearance[show_list_buttons]': '1',
                        'appearance[show_price]': '1',
                        'appearance[show_price_values]': '1',
                        'appearance[show_product_amount]': '1',
                        'appearance[show_product_options]': '1',
                        'appearance[show_qty]': '1',
                        'appearance[show_sku]': '1',
                        'dispatch': 'products.options',
                        select_name[0]: options[0].select(u'./@value').extract()[0]}
            yield FormRequest('http://www.eglobaldigitalstore.co.uk/index.php',
                              formdata=formdata, meta={'loader': loader},
                              callback=self.reload_price,
                              dont_filter=True)
            return
        else:
            out_stock = hxs.select('//span[contains(@class, "out-of-stock")]')
            if out_stock:
                loader.add_value('stock', 0)
            yield loader.load_item()

        for option in options:
            option_text = option.select(u'./text()')[0].extract()
            opt_value = option.select(u'./@value').extract()[0]
            if not opt_value:
                continue
            loader = ProductLoader(item=Product(), selector=hxs)
            res = re.search('(.*?) \(\+\xa3([\d\.,]+)\)', option_text)
            if res:
                option_name, option_price = res.groups()
            else:
                option_name = re.search('(.*)', option_text).groups()[0]
                option_price = u'0.00'

            loader.add_value('name', u'%s %s' % (name, option_name))

            loader.add_value('url', response.url)
            if category:
                loader.add_value('category', category[0])

            loader.add_value('price', str(Decimal(price) + Decimal(option_price)))
            if image_url:
                loader.add_value('image_url', image_url)

            formdata = {'additional_info[get_detailed]': '1',
                        'additional_info[get_discounts]': '1',
                        'additional_info[get_features]': '',
                        'additional_info[get_icon]': '1',
                        'additional_info[get_options]': '1',
                        'additional_info[info_type]': 'D',
                        'appearance[but_role]': 'action',
                        'appearance[capture_options_vs_qty]': '',
                        'appearance[details_page]': '1',
                        'appearance[separate_buttons]': '',
                        'appearance[show_add_to_cart]': '1',
                        'appearance[show_list_buttons]': '1',
                        'appearance[show_price]': '1',
                        'appearance[show_price_values]': '1',
                        'appearance[show_product_amount]': '1',
                        'appearance[show_product_options]': '1',
                        'appearance[show_qty]': '1',
                        'appearance[show_sku]': '1',
                        'dispatch': 'products.options',
                        select_name[0]: opt_value}
            yield FormRequest('http://www.eglobaldigitalstore.co.uk/index.php',
                              formdata=formdata, meta={'loader': loader,
                                                       'opt_value': opt_value},
                              callback=self.parse_identifier, dont_filter=True)

    def parse_identifier(self, response):
        hxs = HtmlXPathSelector(response)
        sku = hxs.select(u'//span[starts-with(@id,"sku_")]/span[not(span)]/text()')[0].extract().strip()
        price = hxs.select(u'//*[@itemprop="price"]/span[@class="price" and @id]/text()')[0].extract().strip()
        loader = response.meta['loader']
        identifier = hxs.select('//input[contains(@name, "product_id")]/@value')[0].extract()
        loader.add_value('identifier', '%s_%s' % (identifier, response.meta['opt_value']))
        loader.add_value('sku', sku)
        loader.replace_value('price', price)
        out_stock = hxs.select('//span[contains(@class, "out-of-stock")]')
        if out_stock:
            loader.add_value('stock', 0)
        if sku.lower() != 'n/a':
            yield loader.load_item()

    def reload_price(self, response):
        hxs = HtmlXPathSelector(response)
        price = hxs.select(u'//*[@itemprop="price"]/span[@class="price" and @id]/text()')[0].extract().strip()
        loader = response.meta['loader']
        loader.replace_value('price', price)
        out_stock = hxs.select('//span[contains(@class, "out-of-stock")]')
        if out_stock:
            loader.add_value('stock', 0)
        yield loader.load_item()
