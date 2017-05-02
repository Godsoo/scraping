from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoader


class ASDAcomSpider(BaseSpider):
    name = u'legouk-asdacom.com'
    allowed_domains = [u'direct.asda.com']
    start_urls = [
        u'http://direct.asda.com/george/kids/lego-construction/D25M8G1C8,default,sc.html'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@id="primary"]//div[@class="productImg"]/a/@href').extract()
        for url in products:
            yield Request(url, callback=self.parse_product)

        prod_count = hxs.select('//span[@class="pagingcount"]/text()').re("[0-9]+")
        if prod_count:
            for page in range(1, int(prod_count.pop())/20+1):
                yield Request(self.start_urls[0] + "?start=%d" % (page * 20))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//*[@itemprop="name"]/@content').extract()
        if not name:
            name = hxs.select('//*[contains(@class, "product-name")]/text()').extract()
        image_url = hxs.select('//*[@itemprop="image"]/@content').extract()
        breadcrumb = hxs.select('//ol[@id="navBreadcrumbs"]/li/h2//a/text()').extract()
        if len(breadcrumb) > 0:
            category = breadcrumb.pop().strip()
        else:
            category = None

        out_stock = False
        if not hxs.select('//input[@id="item_available"][@value="InStock"]').extract():
            out_stock = True

        product_id = hxs.select('//input[@id="georgeMasterProductID"]/@value').extract()
        if not product_id:
            product_id = hxs.select('//input[@id="product_sku_string"]/@value').extract()
        price = hxs.select('//*[@itemprop="price"]/@content').extract()
        if price:
            price = price.pop()
        else:
            price = '0.00'

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price.replace(' ', '').replace(',', '.'))
        loader.add_value('category', category)
        loader.add_value('sku', name, re='- (\d\d\d+)$')
        loader.add_value('brand', "LEGO")
        loader.add_value('identifier', product_id)
        if out_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
