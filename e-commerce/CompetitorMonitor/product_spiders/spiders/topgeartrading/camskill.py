from scrapy import Spider, Request
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class CamSkillSpider(Spider):
    name = 'camskill.co.uk'
    allowed_domains = ['camskill.co.uk', 'competitormonitor.com']
    start_urls = ('http://www.camskill.co.uk/products.php',)

    exclude_word = 'DOT'

    def parse(self, response):
        links = response.xpath('//div[@class="masterCategoryDetail"]/h2/a[not(contains(text(), "Winter"))]/@href').extract()
        links += response.xpath('//h2/following-sibling::strong/a/@href').extract()
        for url in links:
            yield Request(response.urljoin(url))

        if not links:
            for item in self.parse_products(response):
                yield item

    def parse_products(self, response):
        products = response.xpath('//div[@id="productListings"]/article')
        self.log('{} products found'.format(len(products)))
        for product in products:
            try:
                identifier = product.xpath('.//div[@class="productListingPrice"]/a/@href').re(r'/m.*p(\d+)/')[0]
                price = product.xpath('.//section[@class="pricing"]/*/text()').re(r'[\d\.,]+')[0]
                name = product.xpath('.//div[@class="productListingPrice"]/a/@title').extract()[0]
            except:
                continue
            if self.exclude_word in name:
                continue
            image = product.xpath('.//div[@class="subCatProductImage"]//img/@src').extract()[0]
            url = product.xpath('.//div[@class="productListingPrice"]/a/@href').extract()[0]
            url = response.urljoin(url)
            try:
                brand = url.split('/')[-1].split('_')[0]
            except:
                brand = None
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('identifier', identifier)
            loader.add_value('price', price)
            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_value('image_url', image)
            if brand is not None:
                loader.add_value('category', brand)
                loader.add_value('brand', brand)
            yield loader.load_item()
