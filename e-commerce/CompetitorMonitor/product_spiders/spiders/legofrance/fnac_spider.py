import re
import json
import time
import HTMLParser

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import extract_price


class FnacSpider(BaseSpider):
    name = 'legofrance-fnac.com'
    allowed_domains = ['fnac.com']
    start_urls = ['http://www4.fnac.com/s134778/Notre-univers-Lego']

    re_sku = re.compile('(\d\d\d\d\d?)')
    CONCURRENT_REQUESTS = 1


    def start_requests(self):
        lego_lists = ('http://www.fnac.com/Lego/f2108/w-4',
                      'http://www.fnac.com/Lego/m63343/w-4',
                      'http://www4.fnac.com/n198072/Notre-univers-Lego/Meilleures-ventes-LEGO',
                      'http://www4.fnac.com/n227170/Notre-univers-Lego/Meilleures-ventes-DUPLO')

        for list_url in lego_lists:
            yield Request(list_url,
                          callback=self.parse_products,
                          meta={'category': 'Lego'})

        for url in self.start_urls:
            yield Request(url)


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@id="navigation"]/dl/dd/a')
        for category in categories:
            category_name = category.select('text()').extract()[0]
            category_url = category.select('@href').extract()[0]
            yield Request(category_url, callback=self.parse_products, meta={'category': 'Lego'})


    def parse_products(self, response):

        hxs = HtmlXPathSelector(response)
        meta_init = response.meta
        meta = meta_init

        products = hxs.select('//div[@class="Article-itemGroup"]')
        for product in products:
            name = product.select('div/div[@class="Article-infoContent"]/p[@class="Article-desc"]/a/text()').extract()
            if not name:
                continue
            meta['name'] = name[0]
            meta['sku'] = self.re_sku.findall(meta['name'])
            meta['url'] = product.select('div/div[@class="Article-infoContent"]/p[@class="Article-desc"]/a/@href').extract()[0]
            yield Request(meta['url'], callback=self.parse_product, meta=meta)

        products = hxs.select('//ul[@class="articleList"]/li')
        for product in products:
            meta['name'] = product.select('.//div[@class="descProduct"]/p[@class="h2"]/a/text()').extract()[0]
            meta['sku'] = self.re_sku.findall(meta['name'])
            meta['url'] = product.select('.//div[@class="descProduct"]/p[@class="h2"]/a/@href').extract()[0]
            yield Request(meta['url'], callback=self.parse_product, meta=meta)
        urls = hxs.select('//a[contains(@class,"prevnext")]/@href').extract()
        for url in urls:
            yield Request(url, callback=self.parse_products, meta=meta_init)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        meta = response.meta
        identifier = hxs.select(
            '//table[@class="MP"]//a[@class="btn b_sqr_y FnacBtnAddBasket"]/@fnacidproduct').extract()
        if identifier:
            identifier = identifier[0]
        else:
            identifier = hxs.select(
                '//div[@class="buyBox bbMain"]//a[contains(@class,"FnacBtnAddBasket")]/@fnacidproduct').extract()
            if identifier:
                identifier = identifier[0]
            else:
                identifier = response.url.split('/w-4')[0].split('/a')[-1]
        meta['image_url'] = hxs.select('//img[@itemprop="image"]/@src').extract()[0]
        price = hxs.select('//@data-price').extract()
        price = extract_price(price[0]) if price else 0
        meta['price'] = price
        meta['identifier'] = identifier

        item_id = hxs.select('//@data-itemid').extract()

        sellers_urls = [
            "http://www4.fnac.com/api/product/v1/GetListBrandOffers",
            "http://www4.fnac.com/api/product/v1/GetOccasOffers",
            "http://www4.fnac.com/api/product/v1/GetFnacOffer"
        ]

        if item_id:
            for sellers_url in sellers_urls:
                if 'GetListBrandOffers' in sellers_url:
                    sellers_json = {"data":{"content":{"listbrandoffers":{"itemsperpage":"999","order":"7","pagenum":"1","status":"1"},"listoccazoffers":{}},"environment":{"catalog":"1","id":item_id[-1],"url":response.url,"prid":identifier}},"update":{"request":{"type":"listbrandoffers"}}}
                else:
                    sellers_json = {"data":{"environment":{"catalog":1,"prid":identifier,"id":item_id[-1],"url":response.url},"content":{"biletel":{},"comparer":{},"email":{},"reviews":{},"reviewresume":{},"alertprice":{},"listbrandoffers":{"order":7,"pagenum":1,"itemsperpage":10,"status":1},"listoccazoffers":{"order":7,"pagenum":1,"itemsperpage":10,"status":2},"fnacoffer":{"order":0},"offer":{"oref":""},"layers":{},"basketitems":{},"availabilityalerting":{},"bundle":{},"shippingpopin":{},"AdhInfoPopin":{}}},"update":{"request":{"type":"GetOccasOffers","value":""},"response":{"statut":0,"actions":[]}}}

                request = Request(
                    sellers_url,
                    method='POST',
                    dont_filter=True,
                    body=json.dumps(sellers_json),
                    headers={'Content-Type':'application/json'},
                    callback=self.parse_sellers,
                    meta=meta
                )
                request.meta['request'] = request
                request.meta['retry'] = 1
                yield request

        else:
            self.log('WARNING: NO Sellers URL extracted, product ignored! URL: {}'.format(response.url))


    def parse_sellers(self, response):

        html = re.findall(r'<html>(.*)<\/html>', ' '.join(response.body.split()))
        if not html:
#            self.log("Received wrong response, retrying...")
#            if response.meta['retry'] < 5:
#                time.sleep(5)
#                response.meta['retry'] += 1
#                yield response.meta['request']
            return

        pars = HTMLParser.HTMLParser()
        html = pars.unescape(html[0].decode('latin-1'))

        hxs = HtmlXPathSelector(text=html)
        meta = response.meta

        sellers = hxs.select('//li[@class="Offer-item"]')
        self.log(str(len(sellers)))

        for seller in sellers:
            price = ''.join(seller.select('.//strong[@class="product-price"]//text()').extract()).replace(u'\u20ac','.').strip()
            if price.endswith('.'):
                price = price.replace('.', '')

            seller_name = seller.select('.//span[@class="Offer-partnerName"]/text()').extract()
            shipping_cost = '.'.join(seller.select('.//span[@class="Offer-delivery"]/span//text()').extract()).replace(u'\u20ac','').strip()
            if not shipping_cost:
                shipping_cost = '0.0'

            seller_name = seller_name[0] if seller_name else ''

            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', meta['identifier'] + '-' + seller_name)
            l.add_value('name', meta['name'])
            l.add_value('category', meta['category'])
            l.add_value('brand', 'LEGO')
            l.add_value('sku', meta['sku'])
            l.add_value('url', meta['url'])
            l.add_value('shipping_cost', extract_price(shipping_cost))
            l.add_value('price', price)
            l.add_value('image_url', meta['image_url'])
            l.add_value('dealer', 'Fnac - ' + seller_name if seller_name else 'Fnac')
            yield l.load_item()

        if not sellers:
            stock = ''.join(hxs.select("//div[@class='ProductBuyBox']//span[@class='Dispo-txt']/text()").extract()).strip()
            if stock:
                l = ProductLoader(item=Product(), response=response)
                l.add_value('identifier', meta['identifier'] + '-Fnac')
                l.add_value('name', meta['name'])
                l.add_value('category', meta['category'])
                l.add_value('brand', 'LEGO')
                l.add_value('sku', meta['sku'])
                l.add_value('url', meta['url'])
                l.add_value('shipping_cost', 0)
                l.add_value('price', meta['price'])
                l.add_value('image_url', meta['image_url'])
                l.add_value('dealer', 'Fnac')
                yield l.load_item()

    def _encode_price(self, price):
        return price.replace(',', '.').encode("ascii", "ignore")
