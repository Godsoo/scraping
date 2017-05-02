import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product, ProductLoader


class HostaPharmSpider(BaseSpider):
    name = "hostapharm.com.au"
    allowed_domains = ["www.hostapharm.com.au",]
    start_urls = [
        "http://www.hostapharm.com.au/",
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select("//div/div/table/tr/td[2]/a")
        for cat in cats:
            yield Request(
                url=canonicalize_url(
                    urljoin_rfc(
                        base_url, cat.select(".//@href").extract()[0])),
                meta={"cat_name": cat.select(".//text()").extract()[0]},
                callback=self.parse_cat)

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in product, if it is
        products = hxs.select("//div[@id='productbox']/div/a/@href"
            ).extract()
        if products:
            for product in products:
                yield Request(
                    url=canonicalize_url(
                        urljoin_rfc(base_url, product)),
                    meta={"cat_name": response.meta["cat_name"]},
                    callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        #identifier =
        url = canonicalize_url(response.url)
        name = hxs.select("//div[@id='content']/div/strong/text()"
            ).extract()
        price = hxs.select("//div[@id='content']/div/p"
            "/strong[contains(text(), 'Price')]/text()"
            ).extract()[0].split(" ")[1]
        #sku =
        #metadata =
        category = response.meta["cat_name"]
        image_url = canonicalize_url(
            urljoin_rfc(
                base_url, hxs.select("//div[@id='content']/div/div/img/@src"
                ).extract()[0]))
        #brand =
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
        #l.add_value('brand', brand)
        #l.add_value('shipping_cost', shipping_cost)
        yield l.load_item()