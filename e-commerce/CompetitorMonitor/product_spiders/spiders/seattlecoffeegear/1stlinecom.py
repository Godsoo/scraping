import re

from scrapy import log
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product, ProductLoader


prices_range_regex = "\$[\d,]*\.\d*\s*-\s*\$[\d,]*\.\d*"
price_regex = "\$[\d,]*\.\d*"
price_regex_product_page = "[\d,]*\.\d*\s*US Dollars"


class FirstLineComSpider(BaseSpider):
    name = '1st-line.com'
    allowed_domains = ['1st-line.com']
    start_urls = ('http://www.1st-line.com/store/pc/viewcategories.asp',)
    user_agent = (
            'Mozilla/5.0 (Windows NT 5.1; rv:7.0.1) Gecko/20100101 '
            'Firefox/7.0.1')
    ids = {}

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        cats = hxs.select('//div[@class="pcCategoriesWrapper"]//div[@class="pcShowCategoryImage"]//a/@href').extract()
        if cats:
            for cat in cats:
                yield Request(
                        url=canonicalize_url(urljoin_rfc(base_url, cat)),
                        callback=self.parse
                        )
        show_all = hxs.select("//div[@class='pcPagination']/span/a[text()='Show All']/@href").extract()
        if show_all:
            yield Request(
                    url=canonicalize_url(urljoin_rfc(base_url, show_all.pop())),
                    callback=self.parse,
                    )

        products = hxs.select("//div[@class='pcShowProducts']//div[contains(@class, 'pcShowProductName')]/a/@href").extract()
        log.msg(">>>>>>> FOUND %s ITEMS >>>" % len(products))
        if products:
            for product in products:
                yield Request(
                        url=canonicalize_url(urljoin_rfc(base_url, product)),
                        callback=self.parse_product,
                        )

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        url = response.url
        name = hxs.select("///h1[@itemprop='name']/text()").extract()
        try:
            price = hxs.select("//span[@itemprop='price']/text()").extract().pop()
        except:
            price = ""

        try:
            sku = hxs.select("//span[@itemprop='sku']/text()").extract().pop()
        except:
            sku = ""

        identifier = re.search(r'p(\d+).htm$', url).groups()[0]

        product = Product()
        loader = ProductLoader(item=product, response=response)
        loader.add_value('url', url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            loader.add_value('image_url', image_url)

        category = hxs.select("//div[@class='pcPageNav']/a/text()").extract()
        if category:
            loader.add_value('category', category.pop())

        brand = hxs.select("//span[@itemprop='brand']/text()").extract()
        if brand:
            loader.add_value('brand', brand[0].strip())

        out_of_stock = hxs.select('//div[strong[contains(text(),"Availability")]]/text()').re('Currently Out of Stock')
        if not out_of_stock:
            out_of_stock = hxs.select("//link[@itemprop='availability']/../text()").re('Please call')
        if out_of_stock:
            loader.add_value('stock', 0)

        if identifier not in self.ids or price != self.ids[identifier]:
            self.ids[identifier] = price
            yield loader.load_item()
