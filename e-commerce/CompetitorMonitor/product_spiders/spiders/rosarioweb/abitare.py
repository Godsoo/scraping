# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price_eu as extract_price


class AbitareComSpider(BaseSpider):
    name = u'abitare.com'
    allowed_domains = ['abitare.com']
    start_urls = ('http://abitare.com/it/prodotti.aspx',)

    def start_requests(self):
        yield Request('http://abitare.com/it/prodotti.aspx', callback=self.set_product_order)

    def set_product_order(self, response):
        hxs = HtmlXPathSelector(response)
        form_data = {'__EVENTTARGET': 'ctl00$cp_corpo$ddl_ordine',
        'ctl00$cp_corpo$ddl_ordine': 'pc'}
        req = FormRequest.from_response(response,
                                        formdata=form_data,
                                        dont_click=True,
                                        dont_filter=True,
                                        callback=self.set_pagination)
        req = req.replace(url='http://abitare.com/it/prodotti.aspx?lang=it')
        yield req

    def set_pagination(self, response):
        hxs = HtmlXPathSelector(response)
        form_data = {'__EVENTTARGET': 'ctl00$cp_corpo$lb_60'}
        req = FormRequest.from_response(response,
                                        formdata=form_data,
                                        dont_click=True,
                                        dont_filter=True)
        req = req.replace(url='http://abitare.com/it/prodotti.aspx?lang=it')
        yield req

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="div_tit_prod_ele float_dx"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        page = hxs.select('//a[@class="link_paginazione_next_prev" and text()="Avanti"]/@href').extract()
        if page:
            page = page[0].split("'")[1]
            form_data = {'__EVENTTARGET': page}
            req = FormRequest.from_response(response,
                                            formdata=form_data,
                                            dont_click=True,
                                            dont_filter=True)
            req = req.replace(url='http://abitare.com/it/prodotti.aspx?lang=it')
            yield req

    @staticmethod
    def parse_product(response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        try:
            name = hxs.select('//*[@id="cp_corpo_lbl_titolo"]/text()').extract()[0]
            identifier = hxs.select('//*[@id="cp_corpo_lbl_codice"]/text()').extract()[0]
        except:
            return

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name)

        # if not identifier:
        #     return
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        image_url = hxs.select('//*[@id="cp_corpo_img_dettaglio"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//*[@id="cp_corpo_lbl_prezzo"]/text()').extract()
        # if not price:
        #     return
        price = extract_price(price[0].replace(' ', ''))
        loader.add_value('price', price)
        brand = hxs.select('//*[@id="cp_corpo_lbl_produttore"]/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])
        category = hxs.select('//*[@id="div_elenco_cat_lato"]//a[contains(@class,"selected")]/text()').extract()
        if category:
            loader.add_value('category', category[0])
        yield loader.load_item()
