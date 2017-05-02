import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from decimal import Decimal
from utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class RexelOnlineSpider(BaseSpider):
    name = 'newbricoman-rexelonline.it'
    allowed_domains = ('rexelonline.it',)
    start_urls = ('http://rexelonline.it',
                  'http://www.rexelonline.it/Elenco.aspx?p=1')
    download_delay = 0

    def __init__(self, *args, **kwargs):
        super(RexelOnlineSpider, self).__init__(*args, **kwargs)
        self.ean_codes = {}
        self.model_codes = {}
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('EAN', None):
                    self.ean_codes[row['EAN']] = row['Code']
                if row.get('model', None):
                    self.model_codes[row['model'].lower()] = row['Code']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select(u'//tr[contains(@id,"Left_Menu_Categoria")]//a/@href').extract()
        categories += hxs.select(u'//tr[contains(@id,"SottoCategorie")]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(u'http://www.rexelonline.it/', url)
            yield Request(url)
        next_page = hxs.select(u'//input[@name="ctl00$ContentPlaceHolderBody$DataPagerTop4$ctl00$ctl00" and not(@disabled)]').extract()
        if next_page:
            item_options = {}
            for input_ in hxs.select(u'//form[@name="aspnetForm"]//input'):
                    name = input_.select(u'./@name')[0].extract()
                    value = input_.select(u'./@value')
                    value = value[0].extract() if value else u''
                    item_options[name] = value
            item_options.update({'ctl00$ContentPlaceHolderBody$DataPagerTop4$ctl00$ctl00.x': '9', 'ctl00$ContentPlaceHolderBody$DataPagerTop4$ctl00$ctl00.y': '10'})
            yield FormRequest(response.url, formdata=item_options, dont_filter=True)
        products = hxs.select(u'//a[contains(@id,"ListaProdotti")]/@href').extract()
        for url in products:
            url = urljoin_rfc(u'http://www.rexelonline.it/', url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        category = hxs.select(u'//div[a[contains(@id,"History_Scheda")]]/a/text()').extract()
        category = u' > '.join([x.strip() for x in category if len(x.strip()) > 1])
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        try:
            name = hxs.select(u'//h2/span/text()')[0].extract().strip()
        except IndexError:
            return
        loader.add_value('name', name)
        loader.add_value('category', category)
        identifier = hxs.select(u'//span[contains(@id,"CodiceLabel")]/text()').extract()[0].strip()
        alternative_identifier = hxs.select(u'//span[contains(@id,"Codice_produttoreLabel")]/text()').extract()[0].strip()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', alternative_identifier)
        try:
            price = hxs.select(u'//span[contains(@id,"prezzoScontato")]/text()')[0].extract().replace('.', '').replace(',', '.')
        except:
            price = hxs.select(u'//span[contains(@id,"PrezzoLabel")]/text()')[0].extract().replace('.', '').replace(',', '.')
        price = re.sub(u'[^\d\.]', '', price)
        price = str(float(price) * 1.21)
        loader.add_value('price', price)
        image_url = hxs.select(u'//img[contains(@id,"ImgProdotto")]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            loader.add_value('image_url', image_url)

        price = extract_price(price)

        if price < Decimal(60):
            loader.add_value('shipping_cost', '8.00')

        yield loader.load_item()
