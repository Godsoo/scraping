from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import urllib
import re


class BabylandSeSpider(BaseSpider):
    name = 'babyland.se'
    allowed_domains = ['babyland.se']
    start_urls = ('http://www.babyland.se/lego_marke/leksaker/?p=99',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class,"prodbox prodbox_2")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            product_name = product.select('.//a[@class="prodbox_title"]/text()').extract()[0]
            image_url = product.select('.//div[@class="prodbox_picture"]//img[1]/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            product_loader.add_value('name', product_name)
            product_loader.add_value('category', 'LEGO')
            product_loader.add_value('brand', 'LEGO')
            url = product.select('.//a[@class="prodbox_title"]/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            sku = ''
            for match in re.finditer(r'(\d\d\d\d\d?)', url):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            try:
                price = product.select(
                    './/div[@class="buy-area"]//span[@class="sale" or @class="price"]/span/text()').extract()[0]. \
                    strip().replace(' ', '')
            except:
                price = '0.00'
            product_loader.add_value('price', extract_price(price))
            identifier = product.select(
                './/div[@class="prodbox_buttons"]//a[@class="small-btn buy prodbox_buy"]/@onclick').extract()
            if identifier:
                identifier = identifier[0].partition('cart_add(')[2].split(',')[0]
                product_loader.add_value('identifier', identifier)
                product = product_loader.load_item()
                yield product
            else:
                product_loader.add_value('stock', 0)
                product = product_loader.load_item()
                yield Request(product['url'], callback=self.parse_identifier, meta={'product': product})

        list_params = urllib.quote(hxs.select('//input[@name="list_params"]/@value').extract()[0])
        pages = hxs.select('//div[@class="list_filter_pages"]/div/text()').extract()
        for page in pages:
            next_ = urljoin_rfc(base_url,
                                "reload.req.php?page=dolist.req&subpage=" + page + "&i={}".format(list_params))
            next_ = next_.format(list_params)
            yield Request(next_, meta=response.meta)

    @staticmethod
    def parse_identifier(response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        product['identifier'] = hxs.select('//*[@id="variation_id"]/@value').extract()[0]
        yield product
