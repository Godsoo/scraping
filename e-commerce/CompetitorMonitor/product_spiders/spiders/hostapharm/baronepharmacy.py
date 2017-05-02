import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product, ProductLoader


class BaronePharmacySpider(BaseSpider):
    name = "baronepharmacy.com.au"
    allowed_domains = ["www.baronepharmacy.com.au",]
    start_urls = [
        "http://www.baronepharmacy.com.au/sitemap.php",
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select("//table/tr/td/a[@class='catbg']")
        for cat in cats:
            yield Request(
                url=canonicalize_url(
                    cat.select(".//@href").extract()[0]),
                meta={"cat_name": cat.select(".//text()").extract()[0]},
                callback=self.parse_cat)

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        next_page = hxs.select("//a[contains(@title, 'Next Page')]/@href"
            ).extract()
        if next_page:
            yield Request(
                url=canonicalize_url(next_page[0]),
                meta={"cat_name": response.meta["cat_name"]},
                callback=self.parse_cat)

        # Dive in product, if it is
        products = hxs.select("//table/tr/td//a[@class='prodname']/@href"
            ).extract()
        if products:
            for product in products:
                yield Request(
                    url=canonicalize_url(product),
                    meta={"cat_name": response.meta["cat_name"]},
                    callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if not hxs.select("//table[@class='infoBoxContents']/tr"
            "/td[contains(text(), 'Product not found!')]").extract():
            # Fill up the Product model fields
            #identifier =
            url = canonicalize_url(response.url)
            name = hxs.select("//table/tr/td/h1/text()").extract()
            price = hxs.select(
                "//table/tr/td/span[@class='productOurPrice']/strong/text()"
                ).extract()
            if not price:
                price = hxs.select(
                    "//table/tr/td[@class='product-price']/text()"
                    ).extract()[0]
                if not price:
                    price = ""
            try:
                sku = hxs.select(
                    "//table/tr/td/h1/span[@class='smallText']/text()"
                    ).extract()[0].replace("[", "").replace("]", "")
            except:
                sku = ""
            #metadata =
            category = response.meta["cat_name"]
            image_url = canonicalize_url(hxs.select(
                "//table/tr/td[@class='smallText']/noscript/a/@href"
                ).extract()[0])
            #brand =
            #shipping_cost =

            l = ProductLoader(response=response, item=Product())
            #l.add_value('identifier', identifier)
            l.add_value('url', url)
            l.add_value('name', name)
            l.add_value('price', price)
            l.add_value('sku', sku)
            #l.add_value('metadata', metadata)
            l.add_value('category', category)
            l.add_value('image_url', image_url)
            #l.add_value('brand', brand)
            #l.add_value('shipping_cost', shipping_cost)
            yield l.load_item()