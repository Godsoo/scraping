import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product, ProductLoader


class EPharmacySpider(BaseSpider):
    name = "epharmacy.com.au"
    allowed_domains = ["www.epharmacy.com.au",]
    start_urls = [
        "http://www.epharmacy.com.au/online_prescriptions/sitemap.htm",
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select("//ul/li//a[contains(@href, 'category')]")
        for cat in cats:
            yield Request(
                url=canonicalize_url(cat.select(".//@href").extract()[0]),
                meta={"cat_name": cat.select(".//text()").extract()[0]},
                callback=self.parse_cat)

    def parse_cat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if "warning.asp" in response.url:
            request = FormRequest.from_response(
                response,
                formnumber=1,
                formdata={"agreeWarning": "on"},
                dont_click=True,
                callback=self.parse)
            yield request

        next_page = hxs.select("//a[contains(text(), 'Next')]/@href"
            ).extract()
        if next_page:
            yield Request(
                url=canonicalize_url(
                    urljoin_rfc(base_url, next_page[0])),
                meta={"cat_name": response.meta["cat_name"]},
                callback=self.parse_cat)

        # Dive in product, if it is
        products = hxs.select(
            "//div[@class='product_tile_row']/div/div"
            "/div[@class='productName_row']/a/@href").extract()
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

        # Check if sexual content
        if "warning.asp" in response.url:
            request = FormRequest.from_response(
                response,
                formnumber=1,
                formdata={"agreeWarning": "on"},
                dont_click=True,
                callback=self.parse_product)
            yield request

        # Fill up the Product model fields
        #identifier =
        url = canonicalize_url(response.url)
        name = hxs.select("//div[@class='ProductPage_ProductName']/text()"
            ).extract()
        price = hxs.select("//div[@class='ProductPage_NormalPrice']/text()"
            ).extract()
        if not price:
            try:
                price = hxs.select(
                    "//div[@class='ProductPage_PrescPrices_PriceRow']"
                    "/div[@class='ProductPage_PrescPrices_PriceTag']/text()"
                    ).extract()[0].strip()
            except:
                price = ""
        sku = hxs.select("//div[contains(text(), 'Product Code:')]/b/text()"
            ).extract()
        #metadata =
        category = response.meta["cat_name"]
        img = hxs.select("//div[@class='ProductPage_ProdImage']/a/img/@src"
            ).extract()
        if not img:
            img = hxs.select("//div[@class='ProductPage_ProdImage']/img/@src"
                ).extract()
        try:
            image_url = canonicalize_url(urljoin_rfc(base_url, img[0]))
        except:
            image_url = ""
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