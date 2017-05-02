import os
import re
from urlparse import urljoin

from scrapy.http import Request, HtmlResponse
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class ToysRUsSpider(BaseSpider):

    name = 'legouk-toysrus.co.uk'
    allowed_domains = ['toysrus.co.uk']
    start_urls = ['http://www.toysrus.co.uk/toys/s/_/N-0?Dy=1&No=0&Nrpp=96&Ntt=lego+lego&Nty=1&x=0&y=0']


    def parse(self, response):

        hxs = HtmlXPathSelector(response)

        next_page = hxs.select('//a[img[contains(@alt, "Next")]]/@href').extract()
        if next_page:
            next_page = urljoin(response.url, next_page[0])
            yield Request(next_page, meta=response.meta, callback=self.parse)

        products = set(hxs.select(u'//ul[@class="table result-list"]//div[@class="label"]/a/@href').extract())
        for url in products:
            url = urljoin(response.url, url)
            yield Request(url, meta=response.meta, callback=self.parse_product)


    def parse_product(self, response):

        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select(u'//div[@class="product-title"]/h1/text()').extract()
        if not name:
            self.log('ERROR: no product NAME found! URL:{}'.format(response.url))
            retries = response.meta.get('retries', 0)
            if retries < 3:
                meta = response.meta
                meta['retries'] = retries + 1
                yield Request(response.url, meta=meta, callback=self.parse_product)
                return

        name = name[0].strip()
        if 'LEGO' not in name.upper():
            self.log('ERROR: not a LEGO product URL:{}'.format(response.url))
            return

        loader.add_value('name', name)

        prod_id = response.url.split('/')[-1]
        loader.add_value('identifier', prod_id)

        loader.add_value('url', response.url)

        price = hxs.select(u'//div[@class="price clearfix"]//span[@class="sale strong block"]/text()').extract()
        if price:
            loader.add_value('price', price[0])
        else:
            loader.add_value('price', '0.00')

        product_image = hxs.select('//a[@id="mainImage"]/img/@src').extract()
        if product_image:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            loader.add_value('image_url', image)

        category = hxs.select('//ul[@class="breadcrumb"]/ul/li/a/text()').extract()
        if len(category) >= 2:
            loader.add_value('category', category[1].strip())

        sku = re.search('\(([\d]+)\)$', loader.get_output_value('name'))
        if not sku:
            self.log('ERROR: no SKU found! URL:{}'.format(response.url))
        else:
            loader.add_value('sku', sku.group(1))

        loader.add_value('brand', 'Lego')
        yield loader.load_item()
