from scrapy import Spider, Request
from w3lib.url import add_or_replace_parameter
from product_spiders.items import Product
from tigerchefloader import TigerChefLoader as ProductLoader

from tigerchefitems import TigerChefMeta


class KatomSpider(Spider):
    name = 'katom.com'
    allowed_domains = ['katom.com']
    start_urls = ['http://www.katom.com']

    def parse(self, response):
        # Main categories
        for cat_url in response.xpath('//ul[@id="main-nav"]/li/a/@href').extract():
            yield Request(response.urljoin(cat_url))

        sub_categories = response.xpath('//div[contains(@class, "sub-categories")]'
                                        '/div/div//p/a/@href').extract()
        for sub_cat in sub_categories:
            yield Request(add_or_replace_parameter(
                response.urljoin(sub_cat), 'sort', 'lowest'))

        categories = response.xpath('//ul[@class="category"]/li/a/@href').extract()
        categories += response.xpath('//a[contains(@class, "shop-all-button")]/@href').extract()
        categories += response.css('.subcat-panel ::attr(href)').extract()
        for url in categories:
            yield Request(add_or_replace_parameter(
                response.urljoin(url), 'sort', 'lowest'))

        next_page = response.xpath('//ul[@class="pagination"]/li/a[@class="next"]/@href').extract()
        if next_page:
            yield Request(url=response.urljoin(next_page[0]))

        products = response.xpath('//div[contains(@class, "product")]')
        for product_xs in products:
            url = product_xs.xpath('a/@href').extract()
            if not url:
                continue
            product_loader = ProductLoader(item=Product(), selector=product_xs)
            product_loader.add_value('url', url)

            try:
                sku = product_xs.xpath('p[@class="product-sku"]/text()').re('KaTom #: (.*)')[0]
            except:
                sku = None
            product_loader.add_value('sku', sku)
            product_loader.add_value('identifier', sku)
            product_loader.add_xpath('name', 'a/@title')
            product_loader.add_css('image_url', '.img ::attr(src)')
            product_loader.add_xpath('category', '//h1[@class="title"]/text()')

            product = product_loader.load_item()
            if len(product.get('sku', '').split('-')) > 1:
                product['sku'] = '-'.join(product['sku'].split('-')[1:])

            yield Request(
                        url=product_loader.get_output_value('url'),
                        meta={"product": product},
                        callback=self.parse_product)

    def parse_product(self, response):
        product = response.meta['product']

        product_loader = ProductLoader(Product(product), response=response)
        product_loader.add_xpath('price', '//meta[@property="og:price:amount"]/@content')
        product_loader.add_value('price', 0)

        name = response.xpath('//div[@class="product-info"]/p[@class="h1"]/text()').extract()

        img_url = response.xpath('//img[@class="mainImgFix"]/@src').extract()
        if not img_url:
            self.log("ERROR img not found")
        else:
            product_loader.add_value('image_url', img_url[0])

        category = response.xpath('//ol[contains(@class, "breadcrumb")]/li/a/text()').extract()
        if not category:
            self.log("ERROR category not found")
        else:
            product_loader.add_value('category', category[-1])


        brand = response.xpath('//div[@class="logo-area"]/a/@title').extract()
        if not brand:
            brand = response.xpath('//td[contains(text(), "Manufacturer")]/following-sibling::td/text()').extract()
        if not brand:
            self.log("ERROR brand not found")
        else:
            product_loader.add_value('brand', brand[0])

        product = product_loader.load_item()

        if name:
            product['name'] = name[0].strip()

        sold_as = response.xpath('//strong[@class="price"]/span/text()').extract()
        metadata = TigerChefMeta()
        metadata['sold_as'] = sold_as[0].split('/ ')[-1] if sold_as else '1 ea'
        product['metadata'] = metadata

        yield product
