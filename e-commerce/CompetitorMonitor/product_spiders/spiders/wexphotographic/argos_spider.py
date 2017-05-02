import urlparse
import os
import xlrd

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class ArgosSpider(BaseSpider):
    name = 'wexphotographic-argos.co.uk'
    allowed_domains = ['argos.co.uk']
    start_urls = [
        'http://www.argos.co.uk/static/Browse/ID72/33008331/c_1/1|category_root|Technology|33006169/c_2/2|cat_33006169|Cameras+and+camcorders|33008331.htm']

    rotate_agent = True

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # categories and subcategories
        for cat_href in hxs.select("//div[@id='categories']//li/a/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), cat_href)
            )

        # promotional
        for promo_href in hxs.select("//div[@class='ss-row']//a[h2 and img]/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), promo_href)
            )

        # products
        for product in hxs.select("//dl[@name]"):
            product_link = product.select(".//dd[contains(concat('',@class,''), 'image')]/a/@href").extract()[0]
            self.log(product_link)
            yield Request(
                product_link,
                callback=self.parse_product
            )

        # products next page
        for next_page in set(hxs.select("//a[@rel='next']/@href").extract()):
            yield Request(
                next_page
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        url = response.url

        options = hxs.select('//a[contains(@id, "pickerItem")]/@href').extract()
        for option in options:
            option_url = urlparse.urljoin(get_base_url(response), option)
            yield Request(option, callback=self.parse_product)

        l = ProductLoader(item=Product(), response=response)

        name = hxs.select("//div[@id='pdpProduct']/h1/text()").extract()
        if not name:
            self.log("ERROR! NO NAME! %s" % url)
            log.msg('ERROR! NO NAME!')
            if response.url.endswith('.htm'):
                yield Request(response.url.replace('.htm', '.html').replace('beta/', ''), callback=self.parse_product)
            return
        name = name[0].strip()
        l.add_value('name', name)


        price = hxs.select("//span[contains(@class, 'actualprice')]/span/text()").extract()
        #if not price:
        #    price = hxs.select("//li[@class='price']/text()").extract()
        price = extract_price("".join(price))
        l.add_value('price', price)

        sku = hxs.select("//li//text()[contains(., 'EAN')]").extract()
        #if not sku:
        #    sku = hxs.select("//p//text()[contains(., 'EAN')]").re('EAN: (.*).')
        if sku:
            sku = sku[0].split(":")[-1].split('.')[0].strip()

            l.add_value('sku', sku)

        identifier = response.url.split('/')[-1].split('.')[0]
        l.add_value('identifier', identifier)
        categories = hxs.select("//div[@id='breadcrumb']//li/a/text()").extract()[-3:]
        #if not categories:
        #    categories = hxs.select('//ol[@class="breadcrumb"]//li/a/text()').extract()[-3:]
        l.add_value('category', categories)
        image_url = hxs.select("//div[@id='pdpMedia']//div[@id='main']/img[1]/@src")
        #if not image_url:
        #    image_url = ''
        l.add_value('image_url', image_url)
        l.add_value('url', url)
        l.add_xpath('brand', "//strong[@class='pdp-view-brand-main']/text()")
        product = l.load_item()


        yield product
