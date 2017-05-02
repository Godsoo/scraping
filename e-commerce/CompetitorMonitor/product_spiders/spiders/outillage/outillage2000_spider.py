from string import join
import re
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from product_spiders.items import Product, ProductLoader


class OutillageSpider(BaseSpider):
    name = "outillage2000"
    base_url = "http://www.outillage2000.com/"
    allowed_domains = ["outillage2000.com"]
    start_urls = [base_url,
                  "http://www.outillage2000.com/advanced_search_result.php?keywords=%25&x=0&y=0"]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//*[@id="nav"]//li/a/@href').extract()
        for cat in categories:
            url = urljoin_rfc(get_base_url(response), cat)
            yield Request(url)

        # subcategories
        subcategories = hxs.select('//div[@class="block-content"]//li[contains(@class, "nav-item")]/a/@href').extract()
        for subcat in subcategories:
            url = urljoin_rfc(get_base_url(response), subcat)
            yield Request(url)

        # next-pages
        next =hxs.select('//li[@class="next"]/a/@href').extract()
        if next:
            url = urljoin_rfc(get_base_url(response), next[0])
            yield Request(url)

        # products
        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # products
        products = hxs.select('//div[contains(@class,"product-container")]//div[@class="product-image"]/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        # subproducts
        subproducts = hxs.select('//form[@name="buy_now"]/div[@class="boxContent"]//a/@href').extract()
        for subprod in subproducts:
            url = urljoin_rfc(get_base_url(response), subprod)
            yield Request(url, callback=self.parse_product)
        if subproducts:
            return

        url = response.url
        name = join(hxs.select('//div[@class="product-name"]/h1/text()').extract())
        price = hxs.select('//form//div[@class="price-box"]//p/span[contains(@id, "product-price-")]/text()').extract()
        if not price:
            price = hxs.select('//form[@id="product_addtocart_form"]//div[@class="price-box"]//span[@class="price-including-tax"]/span[@class="price"]/text()').extract()
        # remove euro sign and replace ',' with '.' in the price
        if price:
            price = price[0]
            price = ''.join(price.split()).replace(u',', u'.').replace(u'\xe2', u"").strip()
        # if there is a discount the price is in another element
        else:
            price = join(hxs.select('//form//div[@class="price-box"]/span[contains(@id, "product-price-")]/span[@class="price"]/text()').extract())
            price = ''.join(price.split()).replace(u',', u'.').replace(u'\xe2', u"").strip()

        # strip html tags from name
        name = re.sub('<[^<]+?>', '', name)

        product_loader = ProductLoader(item=Product(), selector=name)
        category = hxs.select('//div[contains(@class, "breadcrumb")]/ul/li/a/text()').extract()
        if not category:
            self.log('ERROR No category found!')
        else:
            product_loader.add_value('category', category[0])
        image = hxs.select('//a[@id="zoom1"]/@href').extract()
        if not image:
            self.log("ERROR image not found")
        else:
            image = urljoin_rfc(get_base_url(response), image[0].strip())
            product_loader.add_value('image_url', image)
        product_sku = hxs.select('//div[@class="sku"]/text()').extract()
        if not product_sku:
            self.log("ERROR SKU not found")
        else:
            sku = product_sku[0]
            #if len(sku) < 7:
            #    self.log("ERROR SKU not found")
            #else:
            #   sku = sku[6:-1].strip()
            product_loader.add_value('sku', sku)
        product_id = hxs.select('//input[@name="product"]/@value').extract()
        if not product_id:
            self.log("ERROR product_id not found, skipping this product: " + response.url)
            return
        else:
            product_loader.add_value('identifier', 'new_id_' + str(product_id[0]))
        product_loader.add_value('name', name)
        product_loader.add_value('url', response.url)
        product_loader.add_value('price', price)
        product_loader.add_value('stock', 1)

        if product_loader.get_output_value('name'):
            yield product_loader.load_item()
