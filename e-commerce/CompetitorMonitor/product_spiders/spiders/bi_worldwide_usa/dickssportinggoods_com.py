from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
import demjson
import re
from lxml.etree import XMLSyntaxError

from biwmeta import BIWMeta

class DickssportinggoodsComSpider(BaseSpider):
    name = 'dickssportinggoods.com'
    allowed_domains = ['dickssportinggoods.com']
    start_urls = ('http://www.dickssportinggoods.com',)
    errors = []

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)

    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            categories = hxs.select('//div[@id="mainNav"]/ul/li/ul//a/@href').extract()
        except (TypeError, ValueError, XMLSyntaxError):
            request = self.retry(response, "Unknown error on " + response.url)
            if request:
                yield request
            return

        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)


    def parse_category(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)


        try:
            categories = hxs.select('//div[@class="left-nav"]/ul/li/a/@href').extract()
            if not categories:
                categories = hxs.select('//div[contains(@class,"cms-leftnav")]/div[@id="dsp_cat_a"]//ul/li/a/@href').extract()
        except (TypeError, ValueError, XMLSyntaxError):
            request = self.retry(response, "Unknown error on " + response.url)
            if request:
                if isinstance(request, list):
                    for req in request:
                        yield req
                else:
                    yield request
            return

        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

        products = hxs.select('//ul[@id="product-loop"]/li/div/a/@href').extract()

        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        if products:
            pages = hxs.select('//span[@class="pages"][1]/a/@href').extract()
            for url in pages:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            data = re.findall("var productJson = (.*);", hxs.select('//script[contains(text(), "var productJson = ")]/text()').extract().pop(), flags=re.DOTALL)
            data_json = demjson.decode(data[0].replace("\n", "").replace("[,{", "[{"))
        except (TypeError, ValueError, XMLSyntaxError, demjson.JSONDecodeError) as e:
            request = self.retry(response, "Unknown error on " + response.url)
            if request:
                yield request
            return
        except IndexError:
            return

        name = data_json['productTitle']
        if 'price' in data_json['priceData']:
            price = extract_price(data_json['priceData']['price'])
        identifier = data_json['productId']

        sku = identifier

        category = " > ".join(hxs.select('//div[@id="breadcrumbs"]/div/div/a[text()!="Home"]/text()').extract())

        colors = {}
        for color in data_json['availableColors']:
            if 'mainImageURL' in color:
                colors[color['id']] = color['mainImageURL']

        img = data_json['mainImageURL']

        warranty = hxs.select('//select[@id="warranty_0"]/option/text()').extract()
        warranty_price = ''
        if warranty:
            warranty_price = re.search('Replacement - .([\d\.]+)', warranty[-1])
            warranty_price = warranty_price.group(1) if warranty_price else ''
        biw_metadata = BIWMeta()
        biw_metadata['warranty'] = warranty_price

        for item in data_json['skus']:
            if item['price']:
                price = extract_price(item['price'])
            if not price:
                continue
            if item['colorId'] in colors:
                img = colors[item['colorId']]
            stock = 0
            if item.get('size', '').lower() == 'one size':
                item['size'] = ''
            if item.get('color', '').lower() == 'one color':
                item['color'] = ''
            itemname = "%s %s %s" % (name, item.get('color', ''), item.get('size', ''))
            if "IN_STOCK" in item['avail']:
                stock = 1
            if "NO_DISPLAY" in item['avail']:
                continue

            product = Product()
            product['category'] = category
            product['sku'] = sku
            product['url'] = response.url
            product['stock'] = stock
            product['metadata'] = biw_metadata

            if img:
                product['image_url'] = urljoin_rfc(base_url, img)

            loader = ProductLoader(item=product, response=response)
            loader.add_value('identifier', "%s-%s" % (identifier, item['sku_id']))
            loader.add_value('name', itemname)
            loader.add_value('price', price)
            yield loader.load_item()
