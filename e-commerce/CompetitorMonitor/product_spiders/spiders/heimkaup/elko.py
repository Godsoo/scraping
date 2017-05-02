import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

from heimkaupitems import HeimkaupProduct as Product


class ElkoSpider(BaseSpider):
    name = 'heimkaup-elko'
    allowed_domains = ['elko.is']
    start_urls = ('http://elko.is',)

    def _start_requests(self):
        yield Request('http://www.banneke.com/Whisky/Whiskey/International/Amrut_Malt_Whisky_aus_Indien_46_0.70', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        
        categories = response.xpath('//div[@class="carousal-header-container"]/a/@href').extract()
        categories += hxs.select('//ul[@class="nav"]//a/@href').extract()
        categories += hxs.select('//div[@class="span2"]//ul//a/@href').extract()
        for cat in categories:
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse)

        for productxs in hxs.select('//div[contains(@class, "item-list")]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//*[@itemprop="discount-price"]/text()').extract()))
            if product['price'] == 0:
                product['price'] = extract_price_eu(''.join(productxs.select('.//*[@itemprop="price"]/text()').extract()))

            if productxs.select('.//button[contains(@class, "product_out_of_stock")]'):
                product['stock'] = 0
            else:
                product['stock'] = 1

            meta = response.meta
            meta['product'] = product
            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a/@href').extract()[0]), callback=self.parse_product, meta=meta)
            #yield self.fetch_product(request, self.add_shipping_cost(product))
            yield request

    def parse_product(self, response):
        if 'Server is encountered an error' in response.body:
            return
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        loader.add_value('identifier', re.search("shopee.product.rating.showProductRating\(.*'([^']+)','ecshopfx_rating_container'\);", response.body).group(1))
#        loader.add_value('identifier', response.url.split('/')[-1].split('?')[0])
        if not loader.get_output_value('identifier'):
            return
        loader.add_xpath('sku', '//span[@id="ecshopfx_product_serial_value"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h3[@id="producttitle"]/text()')

        loader.add_value('category', re.findall("shopee.breadcrumb.addToBreadCrumbs\('breadcrumb_container','([^']+)'", response.body.decode('utf8'))[:-1])

        img = ['/elko/upload/images/products/ecshop_zoom_' + loader.get_output_value('sku') + '.jpg']
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', 'normalize-space(//td[contains(text(),"Framlei")]/following-sibling::td/text())')
        if not loader.get_output_value('brand'):
            loader.add_value('brand', loader.get_output_value('name').split()[0])
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 0
        return item
