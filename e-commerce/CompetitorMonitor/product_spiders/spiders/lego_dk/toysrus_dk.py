import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, Selector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

class ToysrusSpider(ProductCacheSpider):
    name = 'toysrus.dk'
    allowed_domains = ['toysrus.dk']
    start_urls = ['http://www.toysrus.dk/soegeresultat?q=lego']

    def __start_requests(self):
        yield Request('http://www.toysrus.dk/maerker/lego')
        return
#        yield Request('http://www.toysrus.dk/brands/lego%20friends/dvd-lego-friends-1?id=897765&vid=518881', callback=self.parse_product)
        yield self.mkreq(0)
        yield self.mkreq_duplo(0)

    def mkreq(self, n):
        return Request('http://www.toysrus.dk/layouts/serviceproxy.aspx?s=SearchServiceFE.svc&m=NewSearch',
                method='POST',
                body='{"query":{"A":"{3DBC4985-711F-46F4-818D-5550ACD7F02C}","B":"","C":null,"D":' + str(n) + ',"E":24,"F":"","G":null,"H":null,"I":null,"J":null,"K":null,"L":null,"O":"f0595688-c94e-47f2-b2d6-5b4d9b50b5d5","P":"","Q":"Serier%7CLEGO","R":"html","S":[],"t":[]}}',
                meta={'n':n},
                dont_filter=True
                )

    def mkreq_duplo(self, n):
        return Request('http://www.toysrus.dk/layouts/serviceproxy.aspx?s=SearchServiceFE.svc&m=NewSearch',
                method='POST',
                body='{"query":{"A":"{6211B1C3-43FD-432D-8E33-4C8CD4332411}","B":"","C":null,"D":' + str(n) + ',"E":24,"F":"","G":null,"H":null,"I":null,"J":null,"K":null,"L":null,"O":"f0595688-c94e-47f2-b2d6-5b4d9b50b5d5","P":"","Q":"Serier%7CLEGO%20Duplo","R":"html","S":[],"t":[]}}',
                meta={'n':n},
                dont_filter=True,
                callback=self.parse_duplo
                )

    def parse(self, response):
        #data = json.loads(response.body)
        #html = data['H']
        #if not html:
            #return

        #hxs = HtmlXPathSelector(text='<html>' + html + '</html>')
        
        for url in response.xpath('//a[contains(@id, "NoScriptPageLink")]/@href').extract():
            yield Request(response.urljoin(url))
            
        text = re.sub('(a id[^>]+?)href[^>]+?(href[^>]+?>)', r'\1\2', response.body)
        selector = Selector(text=text)

        for productxs in selector.css('.product'):
            product = Product()
            price = productxs.css('.overlay').xpath('following-sibling::div[1]/div/span[1]/text()').extract_first()
            product['price'] = extract_price_eu(price)
            #if productxs.select('.//div[@class="instock"]'):
                #product['stock'] = '1'
            #else:
                #product['stock'] = '0'
            
            url = productxs.select('.//a/@href').extract_first()
            if 'lego' not in url:
                continue
            request = Request(response.urljoin(url), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        #yield self.mkreq(response.meta['n'] + 1)

    def parse_duplo(self, response):
        data = json.loads(response.body)
        html = data['H']
        if not html:
            return

        hxs = HtmlXPathSelector(text='<html>' + html + '</html>')

        for productxs in hxs.select('//div[@class="product"]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(x.strip() for x in productxs.select('.//div[@class="price"]//text()').extract()))
            if productxs.select('.//div[@class="instock"]'):
                product['stock'] = '1'
            else:
                product['stock'] = '0'

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        yield self.mkreq_duplo(response.meta['n'] + 1)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        # 'id' is not unique
        loader.add_value('identifier', urlparse.parse_qs(urlparse.urlparse(response.url).query)['vid'][0])
        loader.add_value('url', response.url)
        loader.add_xpath('name', '(//h1//text())[1]')
        sku = response.xpath('//h1//text()').extract_first()
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_value('category', response.meta.get('category', 'LEGO'))

        img = hxs.select('//img[@class="royalImage"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 49
        return item
