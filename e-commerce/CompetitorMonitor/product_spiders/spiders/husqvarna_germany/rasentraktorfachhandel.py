from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class RasentraktorFachhandelSpider(BaseSpider):
    name = 'rasentraktor-fachhandel.de'
    allowed_domains = ['rasentraktor-fachhandel.de']
    start_urls = ['http://www.rasentraktor-fachhandel.de/index.php']

    def parse(self, response):
        base_url = get_base_url(response)

        category_urls = response.xpath('//nav[@class="navbar-categories-left"]//a/@href').extract()
        for url in category_urls:
            yield Request(urljoin_rfc(base_url, url))

        products = response.xpath('//a[@class="product-url"]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

        pages = response.xpath('//ul[@class="pagination"]//a/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page))

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(selector=hxs, item=Product())

        prod_name = hxs.select('//h1/*[@itemprop="name"]/text()').extract()
        self.log('Product Name:- \n')
        self.log(str(prod_name) + '\n\n')

        loader.add_xpath('name', '//h1/*[@itemprop="name"]/text()')
        loader.add_xpath('sku', '//dd/span[@itemprop="model"]/text()')
        loader.add_value('url', response.url)

        price = response.xpath('//div[@class="current-price-container"]/span[@itemprop="price"]/@content').extract()
        if not price:
            price = hxs.select('//span[@id="gm_attr_calc_price"]/text()').extract()

        price = price[0]

        loader.add_value('price', price)

        image_url = response.xpath('//div[@id="product_image_swiper"]//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader._add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        loader._add_value('brand', '')
        stock = response.xpath('//*[@class="img-shipping-time"]/img/@src').extract()
        product_id = response.xpath('//input[@id="products-id"]/@value').extract()
        loader.add_value('identifier', product_id[0])
        if not stock:
            loader._add_value('stock', 0)

        # categories = hxs.select('//*[@id="breadcrumb_navi"]/span/a/text()').extract()
        categories = response.xpath('//*[@id="breadcrumb_navi"]/span/a/span/text()').extract()
        total_categories = len(categories)
        i = 0
        for c in categories:
            if i > 0 and i < total_categories - 1:
                loader.add_value('category', c.strip())
            i += 1
        yield loader.load_item()



