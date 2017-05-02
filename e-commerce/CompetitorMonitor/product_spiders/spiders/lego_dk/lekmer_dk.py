from scrapy.spider import Spider, Request
from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class LekmerSpider(Spider):
    name = 'lekmer.dk'
    allowed_domains = ['lekmer.dk']
    start_urls = ('http://lekmer.dk/lego-produkter/',)

    def parse(self, response):
        for productxs in response.xpath('//div[contains(@class, "products-list")]//div[@data-product]'):
            yield Request(productxs.xpath('.//a[@class="product-card-link"]/@href').extract()[0],
                          callback=self.parse_product)

        next_page = response.xpath('//link[@rel="next"]/@href').extract()
        if next_page and not 'Page.Next.Link' in next_page[0]:
            yield Request(response.urljoin(next_page[0]))

    def parse_product(self, response):
        loader = ProductLoader(item=response.meta.get('product', Product()), response=response)

        loader.add_xpath('identifier', '//input[@name="id"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')
        sku = response.xpath('//div[@class="basic-content-body"]//dt[contains(text(), "Artikelnummer")]'
                             '/following-sibling::dd/text()').re(r'(\d{3}\d*)')
        if sku:
            loader.add_value('sku', sku)
        else:
            self.log('No SKU for %s' % (response.url))

        loader.add_xpath('category', '//ul[contains(@class, "breadcrumbs")]/li[position()=last()-1]/a/text()')

        img = response.xpath('//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', response.urljoin(img[0]))

        price = ''.join(response.xpath('normalize-space(//*[@itemprop="price"]/text())').re(r'([\d.,]+)'))
        loader.add_value('price', extract_price_eu(price))
        loader.add_value('brand', 'Lego')
        in_stock = bool(response.xpath('//div[@class="product-info"]//em[@class="mod-success"]//text()').re(r'lager'))
        if not in_stock:
            loader.add_value('stock', 0)
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        if item['price'] >= 1000:
            item['shipping_cost'] = 0
        else:
            item['shipping_cost'] = 79
        return item
