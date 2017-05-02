import json
import re
import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class GiardinoSegretoSpider(BaseSpider):
    name = 'newbricoman-giardino-segreto.net'
    allowed_domains = ('giardino-segreto.net', 'yoursecretgarden.it')
    start_urls = ('http://www.yoursecretgarden.it',)

    def __init__(self, *args, **kwargs):
        super(GiardinoSegretoSpider, self).__init__(*args, **kwargs)
        self.ean_codes = {}
        self.model_codes = {}
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('EAN', None):
                    self.ean_codes[row['EAN']] = row['Code']
                if row.get('model', None):
                    self.model_codes[unicode(row['model'].lower(), errors='ignore')] = row['Code']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select(u'//div[@id="main"]/ul/li//a/@href').extract()
        self.log('categories')
        for url in categories:
            url = urljoin_rfc(base_url, url)
            yield Request(url)
        next_page = None
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)

        category = hxs.select(u'//div[@id="content"]/div[@id="path"]/a/text()').extract()
        category = u' > '.join(category).replace(u'\xa0\xbb\xa0', '')
        products = hxs.select(u'//div[@class="title"]/h2/a/@href').extract()
        for url in products:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product, meta={'category': category})

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        category = response.meta.get('category')

        image_url = hxs.select(u'//div[@id="main_image"]/img/@src').extract()

        options = hxs.select(u'//select[@class="article_selection"]/option/@value').extract()
        if options:
            for option in options:
                formdata = {'itemID': option, 'lang': 'ita', 'quantity': '1', 'pars[loadimages]': '0'}
                req = FormRequest('http://yoursecretgarden.it/assets/snippets/ajax/article.php?ajax=loadArticleData&lang=ita', formdata=formdata, callback=self.parse_options)
                req.meta['category'] = category
                req.meta['image_url'] = image_url
                req.meta['url'] = response.url
                yield req
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        name = hxs.select(u'//span[@class="hide item_name"]/text()')[0].extract().strip()
        loader.add_value('name', name)
        loader.add_value('category', category)
        identifier = hxs.select(u'//input[@id="itemID"]/@value')[0].extract()
        loader.add_value('identifier', identifier)
        identifier = loader.get_output_value('identifier')
        found = False
        if identifier in self.ean_codes:
            loader.add_value('sku', self.model_codes[identifier])
            found = True
        else:
            for model in self.model_codes.keys():
                if len(model) > 3 and model in name.lower():
                    loader.add_value('sku', self.model_codes[model])
                    found = True
                    break
        if not found:
            loader.add_value('sku', '')
        price = hxs.select(u'//td[@id="priceCad"]/text()')[0].extract().replace('.', '').replace(',', '.')
        loader.add_value('price', price)
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            loader.add_value('image_url', image_url)
        yield loader.load_item()

    def parse_options(self, response):
        data = json.loads(response.body)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', data['title'])
        loader.add_value('price', data['price'])
        loader.add_value('identifier', data['articolo'])
        loader.add_value('category', response.meta['category'])
        loader.add_value('image_url', response.meta['image_url'])
        loader.add_value('url', response.meta['url'])
        yield loader.load_item()
