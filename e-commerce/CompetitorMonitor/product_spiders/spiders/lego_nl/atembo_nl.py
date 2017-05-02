import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

class AtemmboSpider(ProductCacheSpider):
    name = 'a-tembo.nl'
    allowed_domains = ['a-tembo.nl']
    start_urls = ['http://a-tembo.nl/lego-webshop.html']

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)

        yield Request('http://a-tembo.nl/webshop/lego/alle-lego-sets.html',
                      self.parse_pages)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for cat in hxs.select('//ul[@class="VMmenu"]/li[position()>1]//a'):
            yield Request(urljoin_rfc(get_base_url(response), cat.select('./@href').extract()[0]),
                          callback=self.parse_pages,
                          meta={'category': cat.select('./text()').extract()[0]})

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)

        category = hxs.select('//h1[contains(@class, "cat-title")]/text()').extract()[0].strip()

        for url in hxs.select('//div[@class="productdesc"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), self.parse_product, meta={'category': category})

        '''
        for productxs in hxs.select('//div[contains(@class, "productdesc")]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//span[@class="PricesalesPrice"]//text()').extract()))
            if productxs.select('//img[@class="availability" and contains(@alt, "voorraad")]'):
                product['stock'] = '1'
            else:
                product['stock'] = '0'

            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//h2/a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, product)
        '''

        for page in hxs.select('//div[@id="bottom-pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page),
                          callback=self.parse_pages, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        loader.add_xpath('identifier', '//input[@name="virtuemart_product_id[]"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        loader.add_value('price', extract_price_eu(''.join(hxs.select('//span[@class="PricebasePriceWithTax"]//text()').extract())))
        sku = ''.join(hxs.select('//h1/text()').extract())
        try:
            loader.add_value('sku', re.search('(\d{3}\d*)', sku).groups()[0])
        except:
            self.log('No SKU for %s' % (response.url))
        loader.add_value('category', response.meta.get('category'))

        img = hxs.select('//figure[@class="main-image"]/a/@href').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', 'lego')
        loader.add_value('shipping_cost', '5.95')
        if hxs.select('//div[contains(@class, "proddesc")]//img[@class="availability" and contains(@alt, "uitverkocht")]'):
            loader.add_value('stock', '0')
        else:
            loader.add_value('stock', '1')

        yield loader.load_item()
