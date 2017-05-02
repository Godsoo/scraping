# -*- coding: utf-8 -*-


"""
Account: SpecSavers UK
Name: specsavers_uk-tescoopticians.com
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4529
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


from scrapy import Spider, FormRequest
from scrapy.utils.url import url_query_parameter
from product_spiders.items import (
    ProductLoaderWithNameStrip as ProductLoader,
    Product,
)


class TescoOpticians(Spider):
    name = 'specsavers_uk-tescoopticians.com'
    allowed_domains = ['tescoopticians.com']

    start_urls = [
        'http://www.tescoopticians.com/contactlenses/',
        'http://www.tescoopticians.com/prescription-glasses/',
        'http://www.tescoopticians.com/sunglasses/']

    def parse(self, response):
        all_products_loaded = response.meta.get('all_products', False) or \
                              url_query_parameter(response.url, 'ItemsPerPage') == 'all'
        if not all_products_loaded:
            if 'contactlenses' in response.url:
                req = FormRequest.from_response(response,
                                                formdata={'ctl00$ContentPlaceHolder1$uxProductCategoryList$ddlItemsPerPage': 'all'},
                                                dont_filter=True,
                                                meta={'all_products': True})
            else:
                req = FormRequest.from_response(response,
                                                formdata={'ctl00$ContentPlaceHolder1$ddlItemsPerPage': 'all'},
                                                dont_filter=True,
                                                meta={'all_products': True})
            yield req
            return

        products = response.xpath('//div[@class="products"]/div[contains(@id, '
                                  '"ctl00_ContentPlaceHolder1_lstSearchResultsProducts")]')
        if not products:
            products = response.xpath('//div[@class="products"]//div[@id="li"]')
        for product_xs in products:
            rel_url = product_xs.xpath('.//div[contains(@class, "thumbnail")]/a/@href').extract()[0]
            url_data = rel_url[1:-1].replace('-', ' ').split('/')
            identifier = ':'.join(url_data).replace(' ', '-').lower()
            brand = ''
            if len(url_data) > 2:
                brand = url_data[1]
            full_url = response.urljoin(rel_url)
            image_url = product_xs.xpath('.//img[contains(@id, "_imgProduct")]/@src').extract()
            if not image_url:
                product_xs.xpath('.//a[@class="imageLink"]/img/@src').extract()
            image_url = response.urljoin(image_url[0]) if image_url else ''
            category = response.xpath('//*[@id="breadcrumbs"]//text()').extract()[-1].replace('|', '').strip()
            loader = ProductLoader(item=Product(), selector=product_xs)
            loader.add_xpath('name', './/a/span/text()|.//h3/a/text()')
            loader.add_value('url', full_url)
            loader.add_value('category', category)
            if brand:
                loader.add_value('brand', brand)
            loader.add_xpath('price',
                             './/h4[contains(@class, "product-price")]//text()|.//h4[contains(@class, "price")]//text()',
                             re=r'[\d\.,]+')
            loader.add_value('identifier', identifier)
            if image_url:
                loader.add_value('image_url', image_url)

            yield loader.load_item()
