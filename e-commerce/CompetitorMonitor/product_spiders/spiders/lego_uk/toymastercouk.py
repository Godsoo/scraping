from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import TakeFirst, Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader


class ToyMasterSpider(BaseSpider):
    name = u'legouk-toymaster.co.uk'
    allowed_domains = ['www.toymaster.co.uk', 'www.toymastershop.co.uk']
    start_urls = [
        u'http://www.toymastershop.co.uk/c-33-lego.aspx'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        c_xpath = '//div[@class="leftcolumncats"]/div[@class="columnboxwrap"]'
        c_xpath += '//li[@class="tame"and not(ul)]'
        c_xpath += '/a[contains(text(), "lego") or contains(text(),'
        c_xpath += '"Lego") or contains(text(), "duplo") or contains(text(), "Duplo")]/@href'

        categories = hxs.select(c_xpath).extract()
        self.log("Number of categories = %d" % (len(categories)))
        for category in categories:
            url = urljoin(base_url, category)
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        p_xpath = '//div[@class="tabsProductCell"]/div[@class="tabsbottomWrapper"]/div'
        p_xpath += '[@class="tabsNameWrapper"]/h2/a/@href'
        products = hxs.select(p_xpath).extract()
        for product in products:
            url = urljoin(base_url, product)
            yield Request(url, callback=self.parse_product)

        # next_page = hxs.select('//div[@class="pagingregion" and position()=last()]/a[img[@alt="Move Next"]]/@href').extract()
        next_page = hxs.select('//div[@class="resultsPaging"]//a[contains(text(), ">>")]/@href').extract()

        if next_page:
            url = urljoin(base_url, next_page[0])
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name_xpath = '//div[@class="productpagetitlewrap"]/h1/text()'
        name = hxs.select(name_xpath).extract().pop().strip()

        quantity = hxs.select('//form/input[@class="AddToCartButton"]/@value').extract()
        if quantity and "Add to Cart" in quantity.pop():
            quantity = None
        else:
            quantity = 0

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', urljoin(base_url, response.url))
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//div[@id="imageWrapperRpt"]/a[@id="zoom1"]/img[@id="zoom2"]/@src', Compose(lambda v: urljoin(base_url, v[0])))
        loader.add_xpath('price', '//div[@class="productpagerightpriceswrap"]/b/text()', TakeFirst(), re="([.0-9]+)")
        loader.add_xpath('category', '//meta[@name="description"]/@content')
        loader.add_value('sku', name, re='(\d\d\d+)')
        loader.add_xpath('identifier', '//form//input[@type="hidden" and @name="ProductID"]/@value', TakeFirst())

        if quantity == 0:
            loader.add_value('stock', 0)

        yield loader.load_item()
