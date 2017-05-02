import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader


class AndroidEnjoyedSpider(BaseSpider):
    name = "android-enjoyed.com"
    allowed_domains = ["www.android-enjoyed.com", ]
    start_urls = [
        "http://www.android-enjoyed.com/new-arrival.html",
        "http://www.android-enjoyed.com/android-phone.html",
        "http://www.android-enjoyed.com/tablets.html",
        "http://www.android-enjoyed.com/accessories-phone.html",
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cat_name = hxs.select(
            "//div[@class='main']//"
            "div[contains(@class, 'category-title')]/h1/text()").extract()

        # Dive in next page
        next_page = hxs.select(
            "//div[@class='pages']/ol/li/a[@title='Next']")
        if next_page:
            yield Request(
                url=next_page.select(".//@href").extract()[0],
                callback=self.parse)

        # Dive in product, if it is
        products = hxs.select(
            "//div[@class='category-products']/ul/"
            "li[contains(@class, 'item')]/a/@href").extract()
        if products:
            for product in products:
                yield Request(
                    url=product,
                    meta={"cat_name": cat_name},
                    callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        # identifier =
        url = response.url
        name = hxs.select("//div[@class='product-name']/h1/text()"
            ).extract()[0].strip()
        price = hxs.select(
            "//div[@class='product-shop']//div[@class='price-box']/*[@class='special-price' or @class='regular-price']/span[@class='price']/text()"
        ).extract()
        if not price:
            price = hxs.select(
                "//div[@class='price-box']/span/span[@class='price']/text()"
                ).extract()
        sku = hxs.select("//div[@class='product-code']/h3/text()"
            ).extract()[0].split(":")[1].strip()
        # metadata =
        category = response.meta["cat_name"]
        image_url = hxs.select("//div[@class='product-img-box']/p/a/@href"
            ).extract()
        # brand =
        # shipping_cost =

        l = ProductLoader(response=response, item=Product())
        # l.add_value('identifier', identifier)
        l.add_value('url', url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('sku', sku)
        l.add_value('identifier', sku)
        # l.add_value('metadata', metadata)
        l.add_value('category', category)
        l.add_value('image_url', image_url)
        # l.add_value('brand', brand)
        # l.add_value('shipping_cost', shipping_cost)
        yield l.load_item()
