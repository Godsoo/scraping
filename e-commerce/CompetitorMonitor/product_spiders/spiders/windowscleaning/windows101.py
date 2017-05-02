import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product
from productloader import WindowsCleaningProductLoader as ProductLoader

class Windows101(BaseSpider):
    name = 'windows101.com'
    allowed_domains = ['windows101.com', 'www.windows101.com']
    start_urls = ('http://www.windows101.com/shop',)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        
        base_url = get_base_url(response)

        # sub products
        hxs = HtmlXPathSelector(response)
        # product_links = hxs.select('//a[contains(@href, "product_info.php")]/@href').extract()
        products = hxs.select('//a[contains(@href, "products_id") and \
                                    not(contains(@href, "review")) and \
                                    not(contains(@href, "notify")) and \
                                    not(contains(@href, "language")) and \
                                    not(contains(@href, "buy_now"))]/@href').extract()
        for url in products:
            if not 'language=' in url:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//td[@class="pageHeading" and not(@align="right")]/text()').extract()[0]
        if name in ['Welcome, Please Sign In', "Let's See What We Have Here"]:
            return
        price = hxs.select('//form//span[@class="productSpecialPrice"]/text()').re('\$(.*)')
        if not price:
            price = hxs.select('//td[@class="pageHeading" and (@align="right")]/text()').re('\$(.*)')
        price = price[0] if price else '0.00'
        sku = hxs.select('//td[@class="pageHeading"]//span[@class="smallText"]/text()').extract()
        if sku:
            sku = sku[0].replace(']', '').replace('[', '')
        else:
            sku = ''
        identifier = re.findall(r'products_id=(\d+)', response.url)[0]
        category = hxs.select('//td[not(@align) and @class="headerNavigation"]//a[@class="headerNavigation"]/text()').extract()
        
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('price', price)
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)
        brand = hxs.select('//td[@class="boxText"]/table//tr/td[@align="center"]/img/@alt').extract()
        if brand:
            brand = brand[0].strip()
            loader.add_value('brand', brand)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        image_url = hxs.select('//td[@class="main"]//a/img[not(contains(@src,"reviews"))]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
        if not image_url:
            image_url = 'http://windows101.com/shop/popup_image.php?pID=%s' % identifier
        loader.add_value('image_url', image_url)
        if len(category) > 1:
            loader.add_value('category', category[-2])
        yield loader.load_item()

    def parse(self, response):
        # categories
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//table[@class="infoBoxContents"]//a[contains(@href, "cPath")]/@href').extract()
        for url in category_urls:
            if not 'language=' in url:
                yield Request(url)

        # products
        product_links = hxs.select('//a[contains(@href, "products_id") and \
                                    not(contains(@href, "review")) and \
                                    not(contains(@href, "notify")) and \
                                    not(contains(@href, "language")) and \
                                    not(contains(@href, "buy_now"))]/@href').extract()
        for product_link in product_links:
            if not 'language=' in product_link:
                yield Request(product_link, callback=self.parse_product)
