import re
import json
import urlparse
import urllib
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider

from heimkaupitems import HeimkaupProduct as Product

class ToysrusSpider(ProductCacheSpider):
    name = 'heimkaup-toysrus'
    allowed_domains = ['toysrus.is']
    start_urls = ('http://www.toysrus.is/Brands',)
    _brands = set()
    _brand_urls = {}

    def __init__(self, *args, **kwargs):
        super(ToysrusSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if spider != self: return
        for name, cat in self._brand_urls.items():
            self.crawler.engine.schedule(Request(cat, meta={'category': name}, callback=self.parse_cat_uid), self)
        if self._brand_urls:
            self._brand_urls = {}
            raise DontCloseSpider('Found pending requests')

    def _start_requests(self):
        yield Request('http://www.banneke.com/Whisky/Whiskey/International/Amrut_Malt_Whisky_aus_Indien_46_0.70', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for b in hxs.select('//div[@class="brands-overview"]//dd/a/text()').extract():
            self._brands.add(b.strip())
        for b in hxs.select('//div[@class="brands-overview"]//dd/a'):
            self._brand_urls[b.select('./text()').extract()[0]] = urljoin_rfc(get_base_url(response), b.select('./@href').extract()[0])
        yield Request('http://www.toysrus.is/Categories', callback=self.parse_cats)

    def parse_cats(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@class="categories" or @class="brands"]//a/@href').extract()
        categories.append('/Categories/Construction Toys')
        for cat in categories:
            yield Request(urljoin_rfc(get_base_url(response), cat), meta={'category': cat.replace('/Categories/', '').replace('/Brands/', '')}, callback=self.parse_cat_uid)
    def parse_cat_uid(self, response):
        hxs = HtmlXPathSelector(response)

        for uid, cat in zip(re.findall("ContextItemId='(.*)';", response.body.decode('utf8')), re.findall("BreadcrumbTaxonomy='(.*)';", response.body.decode('utf8'))):
            meta = dict(response.meta)
            meta['uid'] = uid
            meta['cat'] = cat
            yield self.mkreq(meta, 0)

    def mkreq(self, meta, n):
        meta = dict(meta)
        meta['n'] = n
        return Request('http://www.toysrus.is/layouts/serviceproxy.aspx?s=SearchServiceFE.svc&m=NewSearch',
                method='POST',
                body='{"query":{"A":"' + meta['uid'] + '","B":"","C":null,"D":' + str(n) + ',"E":24,"F":"","G":null,"H":null,"I":null,"J":null,"K":null,"L":null,"O":"f0595688-c94e-47f2-b2d6-5b4d9b50b5d5","P":"","Q":"' + meta['cat'] + '","R":"html","S":[],"t":[]}}',
                meta=meta,
                dont_filter=True,
                callback=self.parse_cat,
                )

    def parse_cat(self, response):
        data = json.loads(response.body)
        html = data['H']
        if not html:
            return

        hxs = HtmlXPathSelector(text='<html>' + html + '</html>')

        for productxs in hxs.select('//div[@class="product"]'):
            product = Product()

            price = ''.join(x.strip() for x in productxs.select('.//div[@class="price_for_one"]//text()').extract())
            if not price:
                price = ''.join(x.strip() for x in productxs.select('.//div[@class="price"]//text()').extract())

            price = price.replace('1 stk.', '').replace('2 pc.', '')
            product['price'] = extract_price_eu(price)
            if productxs.select('.//div[@class="instock"]'):
                product['stock'] = '1'
            else:
                product['stock'] = '0'

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        yield self.mkreq(response.meta, response.meta['n'] + 1)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        # 'id' is not unique
        # 'vid' is not unique as well
        loader.add_value('identifier', urlparse.parse_qs(urlparse.urlparse(response.url).query)['vid'][0] + ':' + urlparse.parse_qs(urlparse.urlparse(response.url).query)['id'][0])
        loader.add_value('sku', urlparse.parse_qs(urlparse.urlparse(response.url).query)['vid'][0])
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')
        loader.add_value('category', urllib.unquote(response.meta.get('category', 'LEGO')))
        name = loader.get_output_value('name').lower()
        for b in self._brands:
            if b.lower() in name:
                loader.add_value('brand', b)
                break

        img = hxs.select('//img[@class="royalImage"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 0
        return item
