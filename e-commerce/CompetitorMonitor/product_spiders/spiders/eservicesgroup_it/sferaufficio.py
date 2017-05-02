# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import extract_price_eu, extract_price2uk


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader



class SFeraUfficio(BaseSpider):

    name = "sferaufficio.com"
    allowed_domains = ["sferaufficio.com"]
    start_urls = ["http://www.sferaufficio.com"]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//nav[@id="main-navigation"]//li//ul//li//a/@href').extract()


        for idx, url in enumerate(category_urls):
            yield Request(urljoin(base_url, url), callback=self.parse_category, meta={'cookiejar':idx})

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)



        ajax_url = '/ajax.php?azione=lista_articoli'
        url = urljoin(base_url, ajax_url)
        #self.log('parse_category %s' % url)
        yield Request(url , callback=self.parse_list, headers={'X-Requested-With': 'XMLHttpRequest'},
                      meta = {'cookiejar': response.meta['cookiejar']}, dont_filter = True)

    def parse_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        #self.log('parse_list %s' % response.url)

        # products_urls = hxs.select('//h5/a/@href').extract()
        # for url in products_urls:
        #     yield Request(urljoin(base_url, url), callback=self.parse_product)

        products = hxs.select('//form[@id="cart-form"]/div')
        for product in products:
            yield self.parse_product_from_list(product, base_url).load_item()


    def parse_product_from_list(self, hxs, base_url):

        loader = ProductLoader(selector=hxs, item=Product())

        loader.add_xpath('name', './/h5/a/text()')

        url = hxs.select('.//h5/a/@href').extract()[0]
        loader.add_value('url', urljoin(base_url, url))

        price = hxs.select('.//span[@class="price"]/text()').extract()
        if price:
            price = price[0].split()[1]
            price = extract_price_eu(price)
        else:
            price = 0
        loader.add_value('price', price)
        loader.add_value('shipping_cost', 0)

        image_url = hxs.select('.//a/img/@src').extract()
        if image_url:
            image_url = image_url[0]
        else:
            image_url = ''
        loader.add_value('image_url', urljoin(base_url, image_url))

        loader.add_xpath('category', './/span[contains(text(), "Categoria:")]/following-sibling::a/text()')

        loader.add_xpath('brand', './/span[contains(text(), "Marca:")]/following-sibling::a/text()')
        loader.add_value('stock', 1)


        loader.add_xpath('sku', './/span[contains(text(), "Cod. articolo:")]/following-sibling::text()')
        loader.add_xpath('identifier', './/span[contains(text(), "Cod. articolo:")]/following-sibling::text()')

        return loader



    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())

        name = hxs.select('//h1//text()').extract()
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        price = hxs.select('//span[@class="price"]/text()').extract()[0]
        price = price.split()[1]
        price = extract_price_eu(price)
        loader.add_value('price', price)
        loader.add_value('shipping_cost', 0)
        image_url = hxs.select('//img/@src').extract()[1]
        loader.add_value('image_url', urljoin(base_url, image_url))
        category = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()[1]
        loader.add_value('category', category.strip())
        brand = hxs.select('//td[text()="Produttore"]/following-sibling::td[1]/a/text()').extract()[0].strip()
        loader.add_value('brand', brand)
        loader.add_value('stock', 1)
        sku = hxs.select('//div[@id="product-single"]//table//tr[2]/td[2]/text()').extract()

        loader.add_xpath('sku', '//td[text()="Codice prodotto"]/following-sibling::td[1]/text()')
        loader.add_xpath('identifier', '//td[text()="Codice prodotto"]/following-sibling::td[1]/text()')

        yield loader.load_item()

