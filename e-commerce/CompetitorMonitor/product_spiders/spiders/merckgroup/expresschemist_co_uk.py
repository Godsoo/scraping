import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

class ExpressChemistSpider(ProductCacheSpider):
    name = 'expresschemist.co.uk'
    allowed_domains = ['expresschemist.co.uk']
    start_urls = ('http://www.expresschemist.co.uk/topbrands.htm',)
    brands = set()
    ids = {}
    errors = []

    fix_ids_urls = {'http://www.expresschemist.co.uk/product_7786_stella-mccartney-stella-edp-spray-30ml.html': '7785/ste0'}

    def _start_requests(self):
        yield Request('http://www.expresschemist.co.uk/About-Clearzal.html', callback=self.parse_product, meta={'product': Product()})
        for url in start_urls:
	  yield Request(url, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
	base_url = get_base_url(response)

        self.brands = set()
        for brand in hxs.select('//h1/../table/tr[3]//a/text()').extract():
            self.brands.add(brand)

        for letter in hxs.select('//@href[contains(., "sitemap")]').extract():
	  yield Request(urljoin_rfc(base_url, letter), callback=self.parse_letter)

        for cat in hxs.select('//ul[@class="qmmc"]//a/@href').extract():
            if cat.strip():
                yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//h2/../table//a/@href').extract():
	  yield Request(urljoin_rfc(base_url, url), callback=self.parse_cat)

        for productxs in hxs.select('//a[@name]/following-sibling::table') \
            + hxs.select('//td[@colspan="3"]'):
            product = Product()
            product['price'] = extract_price(''.join(productxs.select('.//td[contains(text(), "Price:")]//text()').extract()).replace(' ', ''))
            #if productxs.select('.//a[contains(text(),"when this product comes back into stock")]'):
                #product['stock'] = 0
            #else:
                #product['stock'] = 1

            try: request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//font[@size="3" or @size="2"]/a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            except IndexError:
                try: request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//h2/a/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
                except IndexError: continue
            yield self.fetch_product(request, self.add_shipping_cost(product))

#        for page in hxs.select('//ul[@class="page-list"]//a/@href').extract():
#            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse_cat)

    def parse_letter(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
	for url in hxs.select('//hr[1]/../a/@href').extract():
	  yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'product':Product()})

    def parse_product(self, response):
        found = False
        for x in self.parse_cat(response):
            yield x
            found = True

        if found:
            return
        hxs = HtmlXPathSelector(response)
        if hxs.select('//td[contains(., "no longer available")]'):
	  return

        if not response.meta['product'].get('price'):
            price = hxs.select('//b[contains(text(), "Price: ")]/text()').extract() or hxs.select('//td[contains(text(), "Price: ")]/text()').extract()
            if price:
                response.meta['product']['price'] = extract_price(price.pop(0))
        if not response.meta['product'].get('price'):
            return
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')
        loader.add_xpath('sku', 'normalize-space(substring-after(//td[contains(text(), "Product code:")]/text(), ":"))')

        loader.add_xpath('category', '//td[@valign="top"]/a[2]/text()')

	stock = hxs.select('//a[contains(., "when this product comes back into stock")]')
	if stock:
	  stock = 0
	else:
	  stock = 1
	loader.add_value('stock', stock)

        img = hxs.select('//img[@alt and @border="0" and contains(@src,"products")]/@src').extract()
        identifier = hxs.select('//input[@name="productid"]/@value').extract()
        if img:
            if not loader.get_output_value('identifier'):
                parts = img[0].split('/')
                identifier = parts[parts.index('products')+1] + '/' + (loader.get_output_value('sku') or '')
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        elif identifier:
            identifier = identifier.pop() + '/' + (loader.get_output_value('sku') or '')
        else:
            if not loader.get_output_value('identifier'):
                if "item&nbsp;is&nbsp;currently&nbsp;unavailable" in response.body:
                    return
                sku = (loader.get_output_value('sku') or '')
                if not sku:
                    return
                identifier = '/' + sku

        if response.url in self.fix_ids_urls.keys():
            identifier = self.fix_ids_urls[response.url]

        loader.add_value('identifier', identifier)
        name = loader.get_output_value('name')
        for brand in self.brands:
            if brand.lower() in name.lower():
                loader.add_value('brand', brand)
                break
        else:
            try:
                loader.add_value('brand', name.split()[0])
            except IndexError:
                pass
        if identifier not in self.ids or response.meta['product']['price'] != self.ids[identifier]:
            self.ids[identifier] = response.meta['product']['price']
            yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 2.99
        return item
