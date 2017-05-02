import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader


class DWIDigitalCamerasSpider(BaseSpider):
    name = "dwidigitalcameras.com.au"
    allowed_domains = ["www.dwidigitalcameras.com.au",]
    start_urls = [
        "http://www.dwidigitalcameras.com.au/astore/Directory.aspx",
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in categories
        products = hxs.select("//a[starts-with(@class, 'level')]/@href"
            ).extract()
        for product in products:
            yield Request(
                url=urljoin_rfc(base_url, product),
                callback=self.parse_product)
 
    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        #identifier =
        url = response.url
        name = hxs.select("//div[contains(@id, 'DescriptionAjax')]/h1/text()"
            ).extract()
        if name:
            price = hxs.select("//tr[contains(@id, 'trOurPrice')]/td/text()"
                ).extract()
            #sku =
            #metadata =
            bread = hxs.select("//div[@class='CategoryBreadCrumbs']/a")
            if len(bread)>3:
                category = bread[2].select(".//text()").extract()
            else:
                category = bread[1].select(".//text()").extract()

            try:
                image_url = urljoin_rfc(base_url, hxs.select(
                    "//td[@class='productimg']//img[@id='ProductImage']/@src"
                    ).extract()[0])
            except:
                image_url = ""
            brand = hxs.select(
                "//td[@id='mainPanel']/table[2]/tr[1]/td[1]/h4/a[1]/text()"
                ).extract()
            #shipping_cost =

            l = ProductLoader(response=response, item=Product())
            #l.add_value('identifier', identifier)
            l.add_value('url', url)
            l.add_value('name', name)
            l.add_value('price', price)
            #l.add_value('sku', sku)
            #l.add_value('metadata', metadata)
            l.add_value('category', category)
            l.add_value('image_url', image_url)
            l.add_value('brand', brand)
            #l.add_value('shipping_cost', shipping_cost)
            yield l.load_item()