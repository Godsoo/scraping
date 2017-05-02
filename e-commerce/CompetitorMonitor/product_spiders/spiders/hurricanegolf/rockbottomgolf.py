from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from scrapy import log

from product_spiders.items import Product, ProductLoader


class RockBottomGolfSpider(BaseSpider):
    name = "rockbottomgolf.com"
    allowed_domains = [
        "www.rockbottomgolf.com",
        "search.rockbottomgolf.com"
    ]
    start_urls = [
        "http://www.rockbottomgolf.com/",
        # "http://www.rockbottomgolf.com/golf-swing-trainers-and-practice-aids.html"
        ]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Dive in categories
        cats = hxs.select("//li[contains(@id, yui-gen)]/a")
        for cat in cats:
            yield Request(
                url=canonicalize_url(urljoin_rfc(
                    base_url, cat.select(".//@href").extract()[0])),
                # url = response.url,
                meta={"cat_name": cat.select(".//text()").extract()},
                # meta={"cat_name": "catname"},
                callback=self.parse_cat
            )

    def parse_cat(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        cat_name = response.meta["cat_name"]

        see_all = hxs.select('//td[@class="header-text-p"]/a[contains(text(),"- See All >>>")]/@href').extract()
        if see_all:
            yield Request(
                    url=see_all[0],
                    meta={"cat_name": cat_name},
                    callback=self.parse_cat_all)

        list_all = hxs.select('//td/a[contains(b/text(),"List")]/@href').extract()
        if list_all:
            new_cat_url = list_all[0]
            self.log("LIST ALL FOUND: " + new_cat_url)

            yield Request(
                    url=new_cat_url,
                    meta={"cat_name": cat_name},
                    callback=self.parse_cat_all)

            return

        # Dive in product
        products = hxs.select(
            "//table//span[@class='section-page-para']/a/@href").extract()

        self.log("category: " + response.url)
        self.log("products in category: " + str(len(products)))

        if products:
            for product in products:
                yield Request(
                    url=urljoin_rfc(base_url, product),
                    meta={"cat_name": cat_name},
                    callback=self.parse_product)

    def parse_cat_all(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        cat_name = response.meta["cat_name"]

        # self.log("parse_cat_all: " + response.url)

        next_page = hxs.select('//table[@width="100%"]//a[contains(@href,"search.php") and contains(text(),"Next")]/@href').extract()
        if (next_page):
            next_page_url = next_page[0]

            # self.log("next page FOUND: " + next_page_url)

            yield Request(
                url=next_page_url,
                meta={"cat_name": cat_name},
                callback=self.parse_cat_all
            )

        products = hxs.select('//td/div/a[img]/@href').extract()
        if not products:
            products = hxs.select('//table[@width="100%"]//table[@align="center"]/tr/td/a/@href').extract()
        self.log("category: " + response.url)
        self.log("products in category: " + str(len(products)))

        if products:
            for product in products:
                yield Request(
                    url=urljoin_rfc(base_url, product),
                    meta={"cat_name": cat_name},
                    callback=self.parse_product)
        return

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        sold_out = hxs.select(
            "//form/img[contains(concat('',@src,''), 'soldout')]"
        ).extract()

        # Fill up the Product model fields
        # identifier =
        url = response.url
        name = hxs.select("//div[@class='product-order']/h1/text()").extract()[0]
        shipping_cost = ''
        price = ''
        if sold_out:
            pass
        else:
            price = hxs.select(
                "//div[@id='pit']//li[@class='rbsalep']/text()").extract()
            if not price:
                price = hxs.select(
                    "//div[@id='pit']//ul/table//table//tr[2]/td[2]/text()"
                    ).extract()
                if not price:
                    price = ''

            if not price:
                log.msg(' ::::: Base price :::::')
                log.msg(response.url)
                price = hxs.select('//input[@id="baseprice"]/@value').extract()
                if price:
                    price = price[0]
                else:
                    price = ''

            category = response.meta["cat_name"] if 'cat_name' in response.meta else response.meta['_product']['category']

            image_url = hxs.select("//div[@class='details-left']/table/tr/td/a/img/@src").extract()

            brand = hxs.select('//div[@class="about-item"]/ul/li[contains(b/text(),"Manufacturer:")]/text()').extract()
            if not brand:
                self.log("ERROR brand not found")
                brand = ''

            sku = hxs.select('//div[@class="about-item"]/ul/li[contains(b/text(),"SKU:")]/text()').extract()
            if not sku:
                self.log("ERROR sku not found")
                sku = ''
            else:
                sku = sku[0]

            l = ProductLoader(response=response, item=Product())

            instock = hxs.select('//form[@id="cartForm"]//div[@id="addtocart"]/@id').extract()
            if instock:
                l.add_value("stock", int(1))
            else:
                outofstock = hxs.select('//form[@id="cartForm"]/img[contains(@src,"soldout.gif")]/@src').extract()
                if outofstock:
                    l.add_value("stock", int(0))
                else:
                    self.log("ERROR outofstock not found, instock not found")

            options = hxs.select('//select[@id="Options"]/option[@value!="Select Options"]')

            if options:
                for option in options:
                    l = ProductLoader(response=response, item=Product())
                    l.add_value('url', url)
                    option_name = option.select('text()').extract()[0]
                    option_id = option.select('@value').extract()[0]
                    l.add_value('name', name + ' - ' +option_name)
                    l.add_value('price', price)
                    l.add_value('sku', sku)
                    l.add_value("identifier", sku+'-'+option_id)
                    l.add_value('category', category)
                    l.add_value('image_url', image_url)
                    l.add_value('shipping_cost', shipping_cost)
                    if instock:
                        l.add_value("stock", int(1))
                    else:
                        l.add_value("stock", int(0))

                    if brand:
                        l.add_value('brand', brand)

                    yield l.load_item()
            else:
                l.add_value('url', url)
                l.add_value('name', name)
                l.add_value('price', price)
                l.add_value('sku', sku)
                l.add_value("identifier", sku)
                l.add_value('category', category)
                l.add_value('image_url', image_url)
                l.add_value('shipping_cost', shipping_cost)

                if brand:
                    l.add_value('brand', brand)

                yield l.load_item()