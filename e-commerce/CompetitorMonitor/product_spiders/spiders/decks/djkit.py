from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from scrapy.utils.response import get_base_url


class DjKitDecksSpider(BaseSpider):
    name = 'djkit.com_decks'
    allowed_domains = ['djkit.com']
    start_urls = ['http://www.djkit.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="left"]//ul[@class="slidingmenu"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        next_pages = hxs.select('//div[@class="page"]/a/@href').extract()
        next_pages += hxs.select('//div[@class="prevnext"]/a[contains(text(),"Next")]/@href').extract()
        for page in next_pages:
            yield Request(urljoin_rfc(base_url, page))

        products = hxs.select('//a[@class="product"]/../../..//div[@class="title"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), self.parse_product)

    def parse_product(self, response):
        URL_BASE = 'http://www.djkit.com'
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//*[@itemprop="name"]/text()').extract()
        if not name:
            self.log("ERROR name not found")
            name = ""
        else:
            name = name[0]


        name = name.strip()
        if 'B-STOCK' in name.upper():
            return

        price = hxs.select('//span[@class="product-variation-value discount-value"]//*[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//*[@itemprop="price"]/text()').extract()
        if not price:
            self.log("ERROR price not found")
            price = ""
        else:
            price = extract_price(price[0].strip())

        sku = hxs.select('//*[@itemprop="sku"]/strong/text()').extract()
        if not sku:
            sku = hxs.select('//*[@itemprop="sku"]/text()').extract()
        if not sku:
            self.log("ERROR sku not found")
        else:
            sku = sku[0]

        product_id = hxs.select('//*[@id="sub"]/input[@name="product"]/@value').extract()
        if not product_id:
            self.log("ERROR ID not found")
            return
        else:
            product_id = product_id[0]

        img_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if not img_url:
            self.log("ERROR img not found")
        else:
            img_url = urljoin_rfc(URL_BASE, img_url[0])

        category = hxs.select('//div[@id="breadcrumbs"]/a[@class="breadlink"]/text()').extract()
        category = category[-1] if category else ''

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('sku', sku)
        loader.add_value('image_url', img_url)
        loader.add_value('identifier', product_id.strip())
        loader.add_value('category', category)

        shipping_cost = '5.50' if float(loader.get_output_value('price')) < 50.00 else '0.00'
        loader.add_value('shipping_cost', shipping_cost)

        stock = hxs.select('//div[@class="delivery-availability"]//text()[normalize-space()]').extract()
        if 'DISCONTINUED' in stock:
            return
        if not ('In Stock' in stock or 'In stock' in stock):
            loader.add_value('stock', 0)
        yield loader.load_item()
