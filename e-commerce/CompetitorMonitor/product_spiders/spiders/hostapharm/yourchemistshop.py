import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product, ProductLoader


class YourChemistShopSpider(BaseSpider):
    name = "yourchemistshop.com.au"
    allowed_domains = ["www.yourchemistshop.com.au",]
    start_urls = [
        "http://www.yourchemistshop.com.au/custom/sitemap",
        ]
    extra_urls = [
        "http://www.yourchemistshop.com.au/body-building.html",
        "http://www.yourchemistshop.com.au/family-planning.html",
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select(
            "//ul[@class='sitemap-list']/li/ul/li/a/@href").extract()
        cats += self.extra_urls
        for cat in cats:
            yield Request(
                url=canonicalize_url(cat),
                callback=self.parse_cat)

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Category name
        try:
            cat_name = response.meta["cat_name"]
        except:
            cat_name = hxs.select(
                "//div[@class='page-title category-title']/h1/text()"
                ).extract()[0].strip()

        subcats = hxs.select(
            "//div[@class='category-item']/table/tr/td/a/@href").extract()
        if subcats:
            for subcat in subcats:
                yield Request(
                    url=canonicalize_url(subcat),
                    meta={"cat_name": cat_name},
                    callback=self.parse_cat)

        next_page = hxs.select(
            "//div[@class='pages']/ol/li/a[@class='next']/@href").extract()
        if next_page:
            yield Request(
                url=canonicalize_url(next_page[0]),
                meta={"cat_name": cat_name},
                callback=self.parse_cat)

        # Dive in product, if it is
        products = hxs.select(
            "//div[@class='category-products']/ul/li/a/@href").extract()
        if products:
            for product in products:
                yield Request(
                    url=canonicalize_url(product),
                    meta={"cat_name": cat_name},
                    callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        #identifier =
        url = canonicalize_url(response.url)
        name = hxs.select("//div[@class='product-details']/p/text()"
            ).extract()
        price = hxs.select(
            "//div[@class='product-cart']/div/span/span[@class='price']"
            "/text()").extract()
        if not price:
            try:
                price = hxs.select(
                    "//div[@class='product-cart']/div"
                    "/p[@class='special-price']/span[@class='price']/text()"
                    ).extract()[0].split(" ")[0]
            except:
                price = ""
        #sku =
        #metadata =
        category = response.meta["cat_name"]
        try:
            image_url = canonicalize_url(hxs.select(
                "//div[@class='product-view-details']"
                "//div[@class='product-image']/img/@src").extract()[0])
        except:
            image_url = ""
        #brand =
        sc = hxs.select(
            "//div[@class='product-cart']/p/span[contains(text(), '$')]"
            "/text()").extract()
        if sc:
            shipping_cost = sc[0].split()[0]
        else:
            shipping_cost = ""

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
        l.add_value('shipping_cost', shipping_cost)
        yield l.load_item()