import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product, ProductLoader


class CincottaChemistSpider(BaseSpider):
    name = "cincottachemist.com.au"
    allowed_domains = ["cincottachemist.com.au",]
    start_urls = [
        "http://cincottachemist.com.au/"
            "dept/2-shop-for-medicine-and-first-aid-online",
        "http://cincottachemist.com.au/"
            "dept/5-shop-for-hair-and-body-online",
        "http://cincottachemist.com.au/"
            "dept/9-shop-for-health-and-vitamins-online",
        "http://cincottachemist.com.au/"
            "dept/4-shop-for-mother-and-baby-online",
        "http://cincottachemist.com.au/"
            "dept/31-shop-for-cosmetics-and-fragrance-online",
        "http://cincottachemist.com.au/"
            "dept/30-shop-for-more-online",
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cat_name = hxs.select("//div[@id='pagebody']/div/h3/strong/text()"
            ).extract()
        next_page = hxs.select(
            "//div[@id='paginator']/div[@class='pagnext']/a/@href"
            ).extract()[0]
        if next_page:
            yield Request(
                url=canonicalize_url(urljoin_rfc(base_url, next_page)),
                callback=self.parse)

        # Dive in product, if it is
        products = hxs.select(
            "//div[@id='deptproductgrid']/div[contains(@class, 'pbgroup')]"
            "/div[@class='pbgdesc']/a/@href").extract()
        if products:
            for product in products:
                yield Request(
                    url=canonicalize_url(
                        urljoin_rfc(base_url, product)),
                    meta={"cat_name": cat_name},
                    callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        #identifier =
        url = canonicalize_url(response.url)
        name = hxs.select("//div[@id='productheader']/h3/text()").extract()
        price = hxs.select(
            "//div[@id='productholder']//div[@class='pbgdesc']"
            "/div[@class='price']/text()").extract()
        #sku =
        #metadata =
        category = response.meta["cat_name"]
        image_url = hxs.select("//div[@class='pbgroup']/img/@src").extract()
        #brand =
        #shipping_cost =

        if price:
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