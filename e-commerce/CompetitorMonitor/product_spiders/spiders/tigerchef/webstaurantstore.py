from scrapy import Request, FormRequest
from scrapy.spiders import SitemapSpider
from scrapy.utils.sitemap import sitemap_urls_from_robots
from product_spiders.items import Product
from product_spiders.utils import extract_price
from product_spiders.lib.schema import SpiderSchema
from tigerchefloader import TigerChefLoader as ProductLoader
from tigerchefitems import TigerChefMeta


class WebstaurantStoreSpider(SitemapSpider):
    name = 'webstaurantstore.com'
    allowed_domains = ['webstaurantstore.com']
    sitemap_rules = [('', 'parse_product')]

    def start_requests(self):
        yield Request('http://www.webstaurantstore.com/robots.txt', callback=self.parse_robots)

    def parse_robots(self, response):
        for url in sitemap_urls_from_robots(response.body):
            if 'sitemap-products' in url:
                yield Request(url, callback=self._parse_sitemap, errback=self.on_error, meta={'retry': 5})

    def on_error(self, response):
        retry = int(response.meta.get('retry', 0))
        if retry < 1:
            return
        yield Request(response.url, callback=self._parse_sitemap, errback=self.on_error, meta={'retry': retry - 1})

    def parse(self, response):
        categories = response.xpath('//li[@id="product-categories"]/ul/li/a/@href').extract()
        for cat in categories:
            yield Request(response.urljoin(cat))

        subcategories = response.xpath('//div[@class="overview"]/div/a[@class="btn btn-small btn-info"]/@href').extract()
        subcategories += response.xpath('//div[@id="main"]/div[@class="widget box"]/h2/a/@href').extract()
        for subcat in subcategories:
            yield Request(response.urljoin(subcat))

        product_lists = response.xpath('//div[@class="ag-item"]/a/@href').extract()
        for product_list in product_lists:
            yield Request(response.urljoin(product_list), callback=self.parse_product_list)

    def parse_product_list(self, response):
        next_pages = response.xpath('//div[contains(@class,"pagination")]/ul/li//a/@href').extract()
        for next_page in next_pages:
            yield Request(response.urljoin(next_page), callback=self.parse_product_list)

        products = response.xpath('//div[@class="details"]/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        product_lists = response.xpath('//div[@class="ag-item"]/a/@href').extract()
        for product_list in product_lists:
            yield Request(response.urljoin(product_list), callback=self.parse_product_list)

    def parse_product(self, response):
        schema = SpiderSchema(response)
        data = schema.get_product()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('name', data['Name'])
        loader.add_xpath('category', u'//div[@class="breadcrumbs"]/ul/li[2]/a/text()')
        price = response.xpath('//form[@id="productform"]/input[@name="price"]/@value').extract()
        if price:
            loader.add_value('price', price[0])
        else:
            loader.add_value('price', data.get('offers', {}).get('properties', {}).get('price', '0.0'))

        sku = map(unicode.strip, response.xpath('//span[contains(@class, "mfr-number")]/text()').extract())
        loader.add_value('identifier', data['productID'])
        if sku:
            loader.add_value('sku', sku)
        else:
            loader.add_value('sku', data['productID'].replace('#', ''))

        image_url = data.get('image', '').replace('www.example.com', 'www.webstaurantstore.com')
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))

        brand = data.get('brand', '')
        if not brand:
            brand = response.xpath('//tr[@class="highlight" and .//b[contains(text(), "Manufacturer Name")]]/td[not(b)]/text()').extract()
            brand = brand[0].strip() if brand else ''

        if brand:
            loader.add_value('brand', brand)

        sold_as = response.xpath('//div[@id="subject"]/div/div/p/span[@class="each"]/text()').extract()

        product = loader.load_item()
        if product.get('identifier', '').strip() != '':
            metadata = TigerChefMeta()
            metadata['sold_as'] = sold_as[0].replace('/', '') if sold_as else ''
            product['metadata'] = metadata

            # Add to cart to see the price
            if response.xpath('//*[@itemprop="price" and contains(@class, "strikeOutPrice")][1]'):
                    cart_url = 'http://www.webstaurantstore.com/viewcart.html'
                    inputs = response.xpath('//form[@id="productform"]/input')
                    formdata = dict(zip(inputs.select('./@name').extract(), inputs.select('./@value').extract()))
                    # quantity
                    formdata[u'qty'] = '1'
                    f_request = FormRequest(url=cart_url,
                                            method='POST',
                                            formdata=formdata,
                                            callback=self.parse_price,
                                            meta={'product': product,
                                                  'dont_merge_cookies': True},
                                            dont_filter=True)

                    yield f_request
            else:
                yield product  # loader.load_item()

    def parse_price(self, response):
        product = response.meta['product']
        price = response.xpath('//table[@id="cart"]//tr[@class="odd"]/td[@class="price"]/p/text()').extract()
        product['price'] = extract_price(price[0]) if price else '0'
        yield product
