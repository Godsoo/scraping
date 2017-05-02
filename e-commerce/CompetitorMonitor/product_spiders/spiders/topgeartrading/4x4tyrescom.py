from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class FourxFourTyresCom(Spider):
    name = '4x4tyres.com'
    allowed_domains = ['4x4tyres.co.uk']
    start_urls = ['https://www.4x4tyres.co.uk']
    download_delay = 0.5
    handle_httpstatus_list = [524]

    def parse(self, response):
        yield Request(response.urljoin('/select-your-tyre-size'), callback=self.parse_category, meta={'category':'Tyres'})
        yield Request(response.urljoin('/select-your-wheel-size'), callback=self.parse_category, meta={'category':'Wheels'})

    def parse_category(self, response):
        brands = response.xpath('//div[div/a[contains(text(), "Brand")]]//li/label/a')
        for brand in brands:
            yield Request(brand.xpath('./@href').extract()[0],
                          meta={'category': response.meta['category'],
                                'brand': ''.join(brand.xpath('./text()').extract()).strip()},
                          callback=self.parse_list)

    def parse_list(self, response):
        if response.status == 524:
            yield response.request.replace(dont_filter=True)
            return
        for url in response.xpath('//li[@class="next-page"]/a/@href').extract():
            yield Request(response.urljoin(url), meta=response.meta, callback=self.parse_list)

        category = response.meta['category']
        brand = response.meta['brand']

        products = response.xpath('//div[contains(@class, "item-grid")]/div')
        for product in products:
            loader = ProductLoader(Product(), product)
            url = product.xpath('.//h2/a/@href').extract()
            if not url:
                url = product.xpath('.//a[@class="item-link"]/@href').extract()
            url = url[0]
            loader.add_value('url', response.urljoin(url))
            name = product.xpath('.//h2/a/text()').extract()
            if not name:
                name = product.xpath('.//a[@class="item-link"]//span[@class="product-title"]/span/text()').extract()
            loader.add_value('name', name[0])

            price = product.xpath('.//span[@class="price actual-price"]/text()').extract()[0].strip()
            if not price:
                price = product.xpath('.//span[@class="price actual-price"]//span[@class="product-price"]/text()').extract()[0].strip()
            loader.add_value('price', price)
            stock = product.xpath('.//div[contains(@class, "no-stock")]') or product.xpath('.//span[contains(@class, "no-stock")]')
            if stock:
                loader.add_value('stock', 0)
            loader.add_value('category', category)
            #loader.add_xpath('category', './/li[@class="terain-type"]/text()')
            loader.add_value('brand', brand)
            loader.add_value('identifier', url.rpartition('_')[-1])
            loader.add_value('sku', url.rpartition('_')[-1])

            image_url = product.xpath('./div[1]//img/@src').extract()
            if not image_url:
                image_url = product.xpath('.//span[@class="main-layer"]/span[contains(@class, "picture")]/span/img/@src').extract()
            loader.add_value('image_url', image_url)

            yield loader.load_item()

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        if not loader.get_collected_values('name'):
            return
        loader.add_xpath('price', '//span[@class="full-price"]/text()')
        stock = response.xpath('//div[contains(@class, "low-stock")]') or response.xpath('//div[contains(@class, "no-stock")]')
        if stock:
            loader.add_value('stock', 0)
        categories = response.xpath('//ul[@class="the-breadcrumb-list"]//span[@itemprop="title"]/text()').extract()
        for category in categories:
            if category.title() not in ('Home', 'Search Results'):
                loader.add_value('category', category)
        #loader.add_xpath('category', '//li[@class="terain-type"]/text()')
        brand = response.meta.get('brand')
        if not brand:
            brand = response.xpath('//div[@class="product-brand"]/a/@href').extract()[0]
        loader.add_value('brand', brand.strip('/').replace('-', ' '))
        loader.add_xpath('identifier', response.url.rpartition('_')[-1])
        loader.add_value('sku', response.url.rpartition('_')[-1])
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')

        yield loader.load_item()
