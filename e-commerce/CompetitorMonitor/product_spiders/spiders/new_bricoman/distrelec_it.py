# -*- coding: utf-8 -*-
import time
from decimal import Decimal
from urlparse import urljoin

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import parse_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import extract_price
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider


class DistrelecSpider(BigSiteMethodSpider):
    name = 'newbricoman-distrelec.it'
    allowed_domains = ['distrelec.it',]
    start_urls = ('https://www.distrelec.it/home',)
    website_id = 217

    new_system = True
    old_system = False

    def __init__(self, *args, **kwargs):
        super(DistrelecSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.category_urls = []

    def spider_idle(self, spider):
        if self.category_urls:
            url = self.category_urls.pop()
            request = Request(url, callback=self.parse_products_list)
            self._crawler.engine.crawl(request, self)
        else:
            super(DistrelecSpider, self).spider_idle(spider)

    def parse_full(self, response):
        # this should be in only in full parse
        self.category_urls = [
            'https://www.distrelec.it/alimentatori-batterie-trasformatori',
            'https://www.distrelec.it/automazione',
            'https://www.distrelec.it/elettrotecnica-cavo-non-terminato',
            'https://www.distrelec.it/illuminazione',
            'https://www.distrelec.it/utensileria-saldatura',
            'https://www.distrelec.it/postazione-di-lavoro-manutenzione-meccanica',
        ]

        switch_tax_url = urljoin(get_base_url(response), "/ishopWebFront/home.do?withTax=yes&nocache=" + str(int(time.time() * 1000)))
        r = Request(switch_tax_url, callback=self.main_parse)
        yield r

    def main_parse(self, response):
        url = self.category_urls.pop()

        r = Request(url, callback=self.parse_products_list)
        yield r

    def _get_formdata(self, form_el):
        formdata = {}
        for el in form_el.select(".//input"):
            key = el.select("@name").extract()
            value = el.select("@value").extract()
            if key and value:
                key = key[0]
                value = value[0]
                formdata[key] = value

        for el in form_el.select(".//select"):
            key = el.select("@name").extract()
            value = ""
            if key:
                key = key[0]
                formdata[key] = value

        return formdata

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)

        url_base_parts = parse_url(response.url)
        base_url = '://'.join([url_base_parts.scheme, url_base_parts.netloc])

        categories = hxs.select("//div[@class='catNav']//a/@href").extract()

        for category_url in categories:
            url = urljoin(get_base_url(response), category_url)

            r = Request(url, callback=self.parse_products_list)
            yield r

        search_form = hxs.select("//form[@name='luceneSearchForm'][@method='post']")
        if search_form:
            form_url = search_form.select("@action").extract()[0]
            form_url = urljoin(get_base_url(response), form_url)
            formdata = self._get_formdata(search_form)
            for page_number in set(hxs.select("//table[@class='searchresultsArticlesNavigation']//td[contains(., 'Pagina')]//a/@onclick").re(r'submitPageNumber\((.*)\)')):
                data = formdata.copy()
                data['pageNumber'] = page_number
                data['urlToCall'] = ''
                if 'onlyOnStock' in data:
                    del(data['onlyOnStock'])
                if 'onlyPriceReduced' in data:
                    del(data['onlyPriceReduced'])
                if 'pageSize' in data:
                    del(data['pageSize'])
                if 'trackArtNr' in data:
                    del(data['trackArtNr'])
                if 'trackPosition' in data:
                    del(data['trackPosition'])
                if 'trackProductTitle' in data:
                    del(data['trackProductTitle'])
                r = FormRequest(form_url, formdata=data, callback=self.parse_products_list)
                yield r

        category = hxs.select("//table[@class='LinksKatalogNav']//td[1]/a/h1/text()").extract()
        products = hxs.select("//td[@id='productListCell']/table/tr[td[contains(@class, 'document')]]")
        for p in products:
            name = p.select(".//input[contains(@name, '.shortDescription')]/@value").extract()[0]
            url = p.select(".//input[contains(@name, '.uriPath')]/@value").extract()[0]
            url = urljoin(base_url, url)
            brand = p.select(".//input[contains(@name, '.vendor')]/@value").extract()[0]
            price = p.select(".//input[contains(@name, '.price')]/@value").extract()[0]
            image_url = urljoin(get_base_url(response), p.select(".//input[contains(@name, '.img')]/@value").extract()[0])
            sku = p.select(".//input[contains(@name, '.type')]/@value").extract()[0]
            identifier = p.select(".//input[contains(@name, '.artNr')]/@value").extract()[0]
            stock = p.select(".//input[contains(@name, '.stockValue')]/@value").extract()[0]
            if not stock:
                stock = 0

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_value('category', category)
            loader.add_value('brand', brand)
            loader.add_value('image_url', image_url)
            loader.add_value('sku', sku)
            loader.add_value('identifier', identifier)
            loader.add_value('stock', stock)
            loader.add_value('price', price)

            price = extract_price(price)

            if price < Decimal(100.00):
                loader.add_value('shipping_cost', '10.00')

            yield loader.load_item()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        category = hxs.select("//table[@class='LinksKatalogNav']//td[1]/a/h1/text()").extract()

        identifier = hxs.select('//td[@class="artNr"]/text()').extract()[0]
        sku = hxs.select('//td[preceding-sibling::td[@class="title"][div[text()="Tipo"]]]/text()').extract()[0]
        name = hxs.select('//div[@class="bigTitle"]/h1/text()').extract()[0]

        url = response.url

        brand = hxs.select('//td[preceding-sibling::td[@class="title"][div[text()="Produttore"]]]/text()').extract()
        if brand:
            brand = brand[0]

        price = hxs.select('//tr[2]/td/div[@class="productTablePriceScale"][1]/text()').extract()[0]

        stock = hxs.select("//span[preceding-sibling::img[@class='onStock']]/text()").extract()
        if stock:
            stock = stock[0]
        else:
            if hxs.select("//img[@class='noStock']"):
                stock = 0
            else:
                stock = None

        image_url = hxs.select("//img[@id='firstImagesrc']/@src").extract()
        image_url = urljoin(get_base_url(response), image_url[0])

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name)
        loader.add_value('url', url)
        loader.add_value('category', category)
        loader.add_value('brand', brand)
        loader.add_value('image_url', image_url)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('stock', stock)
        loader.add_value('price', price)

        price = extract_price(price)

        if price < Decimal(100.00):
            loader.add_value('shipping_cost', '10.00')

        yield loader.load_item()
