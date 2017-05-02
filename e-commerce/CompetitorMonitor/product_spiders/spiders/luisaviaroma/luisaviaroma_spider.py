import os
import re
import json
import csv
import urlparse

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class LuisaviaromaSpider(BaseSpider):
    name = 'luisaviaroma.com'
    allowed_domains = ['luisaviaroma.com']
    start_urls = ('http://www.luisaviaroma.com',)

    categories = ["http://www.luisaviaroma.com/CatalogSrv.ashx?data={%22Season%22:%22actual%22,%22Gender%22:%22women%22,%22Age%22:%22A%22,%22SubLine%22:%22%22,%22DesignerId%22:%22063%22,%22CategoryId%22:%22%22,%22ItemSeasonId%22:%22%22,%22ItemCollectionId%22:%22%22,%22ItemId%22:0,%22ColorId%22:%22%22,%22FromSearch%22:false,%22PriceRange%22:%22%22,%22Discount%22:%22%22,%22SizeTypeId%22:%22%22,%22SizeId%22:%22%22,%22Available%22:false,%22NewArrivals%22:false,%22ListaId%22:%22%22,%22ViewExcluded%22:false,%22IsMobile%22:false,%22MenuDataCallback%22:%22menuResponse%22,%22NewArrivalsAutomatic%22:true,%22MaxItemXPage%22:48,%22ResponseTypeString%22:%22TextToEval%22}&time='1402599682472'"]

    def start_requests(self):
        params = {'CallType': 'CurrAndShip',
                  'action': 'save',
                  'myCountryId': 'AE',
                  'myCurrency': 'EUR',
                  'myLangId': 'EN',
                  'myViewCurrency': 'EUR'}

        req = FormRequest(url="http://www.luisaviaroma.com/myarea/getLogIn.aspx", formdata=params)
        yield req

    def parse(self, response):
        with open(os.path.join(HERE, 'luisaviaroma.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Luisaviaroma']:
                    meta = {}
                    meta['category'] = row['Category']
                    meta['brand'] = row['Brand']
                    meta['sku'] = row['Codes']
                    meta['url'] = row['Luisaviaroma']

                    parsed = urlparse.urlparse(row['Luisaviaroma'].replace('#ItemSrv.ashx|', ''))
                    params = urlparse.parse_qs(parsed.query)
                    param_dict = {}
                    for param in params.keys():
                        param_dict[param] = params[param][0]
                    url = 'http://www.luisaviaroma.com/ItemSrv.ashx?itemRequest='+str(param_dict)
                    yield Request(url, callback=self.parse_product, meta=meta)

        for category in self.categories:
            yield Request(category, callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        products = json.loads(re.search('catalogResponse=(.*);pricingResponse', response.body).group(1).replace("'",'"'))
        category = products['DesignerBanner']['Description'].strip()
        products = products['CatalogResults']
        for product in products:
            params =  {'NoContext':'true','SeasonId':str(product['SeasonId']),'CollectionId':str(product['ItemCollectionId']),'ItemId':str(product['ItemId'])}
            url = 'http://www.luisaviaroma.com/ItemSrv.ashx?itemRequest=' + str(params).replace(' ','')
            yield Request(url, callback=self.parse_product, meta={'category':category, 
                                                                                      'url': product['UrlProductEn'],
                                                                                      'brand': category,
                                                                                      'sku':product['Pricing']['ItemKey']['ItemCode']})

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        product = re.search('itemResponse=(.*);', response.body)
        if product:
            product = json.loads(product.group(1))

            meta = response.meta
  
            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', product['ItemKey']['ItemCode'])
            l.add_value('name', product['Designer']['Description'] + ' ' + product['ShortDescription'])
            l.add_value('url', meta.get('url'))
            l.add_value('sku', meta.get('sku'))
            l.add_value('brand', meta.get('brand'))
            image_url = 'http://images.luisaviaroma.com/Big' + product['ItemPhotos'][0]['Path']
            l.add_value('image_url', image_url)
            l.add_value('category', meta.get('category'))
            l.add_value('price', product['Pricing'][0]['InvoicePrice']['FinalPrice'])
            yield l.load_item()
