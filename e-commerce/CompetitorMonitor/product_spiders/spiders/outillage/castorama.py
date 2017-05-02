import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv

from product_spiders.items import Product, ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class CastoramaSpider(BaseSpider):
    name = 'castorama.fr'
    allowed_domains = ['www.castorama.fr', 'castorama.fr']
    start_urls = ('http://www.castorama.fr/store/Pistolet-a-peinture-electrique-et-machine-a-peindre-cat_id_1635.htm?navCount=8&navAction=push&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Outillage-cat_id_1584.htm?navAction=jump&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Aspirateur-et-nettoyeur-cat_id_1585.htm?navAction=jump&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Chauffage-climatisation--traitement-de-lair-cat_id_307.htm?navAction=jump&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Etabli-et-Rangement-garage-cave-atelier-cat_id_3040.htm?navAction=jump&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Rangement-et-dressing-cat_id_3003.htm?navAction=pop&wrap=true&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Construction-et-materiaux-cat_id_472.htm?navAction=jump&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Plomberie-et-traitement-de-leau-cat_id_2267.htm?navAction=jump&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Outil-a-moteur-cat_id_1456.htm?navAction=jump&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Outil-a-main-cat_id_1379.htm?navAction=jump&sortByValue=lowHighPrice',
                  'http://www.castorama.fr/store/Arrosage-et-recuperation-de-leau-cat_id_30.htm?navAction=jump&sortByValue=lowHighPrice')

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
                    return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select(u'//div[contains(@class,"productsListItem")]/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            if 'sortByValue' not in url:
                url += ('?' if '?' not in url else '&') + 'sortByValue=lowHighPrice'
            yield Request(url)

        # pagination
        next_page = hxs.select(u'//div[@class="suivantDivProds"]/a[@class="suivant"]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page)

        # products
        for product in self.parse_product_list(response):
            yield product

    def parse_product_list(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        featured_product = hxs.select(u'//div[@class="featuredProduct"]')
        product_loader = ProductLoader(item=Product(), selector=featured_product)
        url = featured_product.select(u'.//div[@class="fDescription"]/a/@href').extract()
        if url:
            url = urljoin_rfc(get_base_url(response), url[0])
            product_loader.add_value('url', (url.split(';')[0]).split('?')[0])
            product_loader.add_xpath('name', u'.//div[@class="fDescription"]/a/strong/text()')
            identifier = featured_product.select(u'.//input[@name="/com/castorama/CastShoppingCartFormHandler.productId"]/@value').extract()
            if not identifier:
                identifier = featured_product.select('.//div[@class="fIllustration"]//img/@productid').extract()
            if (identifier and not identifier[0].strip()) or not identifier:
                identifier = re.search(r'-([\w]*)\.html', url).groups()
            product_loader.add_value('identifier', identifier[0])
            try:
                product_loader.add_value('image_url',
                                         urljoin_rfc(get_base_url(response),
                                                     featured_product\
                                                     .select('.//div[@class="fIllustration"]//img/@src').extract()[0]
                                                     ))
            except:
                pass
            price_css_classes = [{'tag': 'span', 'class': 'newprice'}, {'tag': 'div', 'class': 'price'}]
            for price_css_class in price_css_classes:
                price = featured_product.select(u'.//' + price_css_class['tag'] + '[@class="' + price_css_class['class'] + '"]/text()').re(u'([0-9\,\.\xa0]+)')
                if price:
                    price = price[0].replace(u'\xa0', '').replace(',', '.')
                    product_loader.add_value('price', price)
                    break
            # if not product_loader.get_output_value('price'):
            product_loader.add_value('stock', 1)
            yield product_loader.load_item()

        products = hxs.select(u'//div[contains(@class,"productsRow")]/div[contains(@class,"productItem")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            url = product.select(u'.//div[@class="prodDecription"]/a/@href').extract()
            if not url:
                continue
            url = urljoin_rfc(get_base_url(response), url[0])
            product_loader.add_value('url', (url.split(';')[0]).split('?')[0])
            product_loader.add_xpath('name', u'.//div[@class="prodDecription"]/a/text()')
            identifier = product.select(u'.//input[@name="/com/castorama/CastShoppingCartFormHandler.productId"]/@value').extract()
            if not identifier:
                identifier = product.select('.//div[@class="illustration"]//img/@productid').extract()
            if (identifier and not identifier[0].strip()) or not identifier:
                identifier = re.search(r'-([\w]*)\.html', url).groups()
            product_loader.add_value('identifier', identifier[0])
            try:
                product_loader.add_value('image_url',
                                         urljoin_rfc(get_base_url(response),
                                                     product\
                                                     .select('.//div[@class="illustration"]//img/@src').extract()[0]
                                                     ))
            except:
                pass
            price_css_classes = [{'tag': 'span', 'class': 'newprice'}, {'tag': 'div', 'class': 'price'}]
            for price_css_class in price_css_classes:
                price = product.select(u'.//' + price_css_class['tag'] + '[@class="' + price_css_class['class'] + '"]/text()').re(u'([0-9\,\.\xa0]+)')
                if price:
                    price = price[0].replace(u'\xa0', '').replace(' ', '').replace(',', '.')
                    product_loader.add_value('price', price)
                    break
            # if not product_loader.get_output_value('price'):
            product_loader.add_value('stock', 1)
            try:
                yield product_loader.load_item()
            except:
                self.log('>>> WARNING: load item error in => %s' % response.url)

        if not products or not featured_product:
            log.msg('Retrying url: %s' % response.url, level=log.WARNING)
            retries = response.meta.get('retries', 0)
            if retries < 3:
                yield Request(response.url, dont_filter=True, meta={'retries': retries + 1})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        hxs = HtmlXPathSelector(response)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//div[@class="productContent"]/h1/text()')
        price = hxs.select('//div[@class="rightColumn rightColumnV2 productDetailsRightColumn"]//div[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="rightColumn rightColumnV2 productDetailsRightColumn"]//span[@class="newprice"]/text()').extract()
        if price:
            price = price[0].strip().replace(u'\xa0', '').replace(' ', '').replace(',', '.')
            product_loader.add_value('price', price)
        # if not product_loader.get_output_value('price'):
        product_loader.add_value('stock', 1)
        identifier = re.search(r'-([\w]*)\.html', response.url).groups()
        product_loader.add_value('identifier', identifier[0])
        product_loader.add_value('image_url',
                                 urljoin_rfc(get_base_url(response),
                                             hxs.select('//div[@class="productImage"]//img/@src').extract()[0]
                                             ))
        try:
            yield product_loader.load_item()
        except:
            self.log('>>> WARNING: load item error in => %s' % response.url)
