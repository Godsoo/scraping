from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

from scrapy import log

class WindowCleaningSupplySpider(BaseSpider):
    name = 'window-cleaning-supply.com'
    allowed_domains = ['www.window-cleaning-supply.com']
    start_urls = ('http://www.window-cleaning-supply.com',)

    def parse(self, response):

        base_url = get_base_url(response)
        #categories
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="Block CategoryList Moveable Panel"]//a')
        for category in categories:
            url = category.select('./@href')[0].extract()
            name = category.select('./text()')[0].extract().strip()
            yield Request(urljoin_rfc(base_url, url), meta={'category': name})

        #next page
        next_page = hxs.select('//div[@class="CategoryPagination"]//div[@class="FloatRight"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=response.meta)

        # products
        product_links = hxs.select('//div[@class="ProductDetails"]/strong/a/@href').extract()
        for url in product_links:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)


    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # products
        product_links = hxs.select('//div[@id="CategoryContent"]//div[@class="ProductDetails"]/strong/a/@href').extract()
        for url in product_links:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)
        if product_links or not hxs.select('//h1/text()'):
            return

        # sub products
        subproduct_urls = hxs.select('//div[@class="ProductDescriptionContainer"]//a/@href').extract()
        if subproduct_urls:
            for url in subproduct_urls:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

        name = hxs.select('//h1/text()')[0].extract()
        if 'MSDS' in name.upper() or 'ABC' in name.upper():
            return
        category = response.meta.get('category', '')
        brand = hxs.select('//div[@class="DetailRow" and div[text()="Brand:"]]/div[@class="Value"]//text()[normalize-space()]').extract()
        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()
        price = hxs.select('//em[@class="ProductPrice VariationProductPrice"]/text()').extract()
        price = price[0] if price else '0.00'
        identifier = hxs.select('//form[@id="productDetailsAddToCartForm"]//input[@type="hidden" and @name="product_id"]/@value')
        if identifier:
            identifier  = identifier[0].extract()
        else:
            log.msg('Product without identifier: ' + response.url)
            return

        sku = hxs.select('//div[@id="sku"]/text()').extract()
        sku = sku[0] if sku else None

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('identifier', identifier)
        if sku:
            loader.add_value('sku', sku)
        loader.add_value('category', category)
        if brand:
            loader.add_value('brand', brand[0].strip())
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)

        yield loader.load_item()
