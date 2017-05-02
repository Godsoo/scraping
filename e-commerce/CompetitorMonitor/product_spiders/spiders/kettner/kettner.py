from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url
from scrapy.http.cookies import CookieJar
from scrapy import log

from product_spiders.items import (Product,
        ProductLoaderWithNameStrip as ProductLoader)

class KettnerSpider(BaseSpider):
    name = 'kettner.fr'
    allowed_domains = ['kettner.fr']
    start_urls = ('http://www.kettner.fr',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//div[@id="menu"]/a/@href').extract()
        for cat in cats:
            yield Request(
                    url=canonicalize_url(cat),
                    callback=self.parse_cat)

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        subcats = hxs.select('//div[@class="menu_left"]//a[@href!="#"]/@href').extract()
        if subcats:
            for subcat in subcats:
                yield Request(
                        url=canonicalize_url(subcat),
                        callback=self.parse_subcat)

    def parse_subcat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        pages = hxs.select('//div[@class="top_pagination"]//a[contains(@href, "DISPLAY_ALL")]/@href').extract()
        if pages:
            yield Request(
                    url=canonicalize_url(pages[0]),
                    callback=self.parse_subcat)

        products = hxs.select('//div[@id="product_list"]//div[@class="Ncaps"]//div[@class="name"]/a/@href').extract()
        if not products:
            meta = response.meta.copy()
            retry = meta.get('retry', 0)
            if retry < 3:
                meta['retry'] = retry + 1
                yield Request(response.request.url,
                              callback=self.parse_subcat,
                              meta=meta,
                              dont_filter=True)
        else:
            for product in products:
                yield Request(
                        url=canonicalize_url(product),
                        callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        try:
            name = hxs.select('//div[@class="main_title"]/h1'
                              '//span[@itemprop="name"]/text()')\
                      .extract()[0].strip()
        except:
            meta = response.meta.copy()
            retry = meta.get('retry', 0)
            if retry < 3:
                meta['retry'] = retry + 1
                yield Request(response.request.url,
                              callback=self.parse_product,
                              meta=meta,
                              dont_filter=True)
            return
        try:
            category = hxs.select('//div[@id="menu"]/a[@class="current"]/@title').extract()[0].strip()
        except:
            category = None
        try:
            image_url = urljoin_rfc(get_base_url(response), hxs.select('//div[@class="img"]//img/@src').extract()[0])
        except:
            image_url = None

        brand = hxs.select('//div[@class="line" and contains(text(), "Marque")]/a/@title').extract()

        if not brand:
            brand = hxs.select('//div[@class="line" and contains(text(), "Marque")]/text()').re(r'Marque.*:(.*)')
        if not brand:
            brand = hxs.select('//div[@class="line brand"]//*/text()').extract()

        brand = brand[0].strip() if brand else None

        try:
            sku = hxs.select('//form[@id="form_add_to_cart"]/input[@name="cell_b6"]/@value').extract()[0].strip()
        except:
            sku = hxs.select('//div[@class="line_ref"]/text()').re(r'(\d+)')[0].strip()

        identifier = hxs.select('//form[@id="form_add_to_cart"]/input[@name="MAIN_ID_PRODUCT"]/@value').extract()[0].strip()

        '''
        for sub_name in hxs.select('//div[@class="choice_list_area"]//option[@selected]/text()').extract():
            name += ' ' + sub_name.strip()
        '''

        loader.add_value('name', name)
        price = hxs.select('//span[@class="price"]/text()').extract()[0]
        price = price.replace(',', '.')
        loader.add_value('price', price)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('category', category)
        loader.add_value('image_url', image_url)
        loader.add_value('brand', brand)
        yield loader.load_item()

        '''
        option_lists = hxs.select('//div[@class="choice_list_area"]//select')
        for option_list in option_lists:
            url = option_list.select('./@onchange').extract()[0]
            url = url.split(',')[2].strip("'")
            options = option_list.select('./option[not(@selected)]/@value').extract()
            for option in options:
                yield Request(
                        url=url+option,
                        callback=self.parse_product)
        '''
