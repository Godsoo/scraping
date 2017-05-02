import os
import csv
from scrapy import Spider, Request
from product_spiders.items import Product
from axemusic_item import ProductLoader
from product_spiders.config import DATA_DIR


class PaShopSpider(Spider):
    name = 'pashop.com'
    allowed_domains = ['pashop.com']
    start_urls = ['http://www.pashop.com/products/store/']

    download_delay = 10

    def __init__(self, *args, **kwargs):
        super(PaShopSpider, self).__init__(*args, **kwargs)
        self._identifier_name = {}

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        url = '/'.join(row['url'].split('/')[:-2]).replace('/detail/', '/manufacturer/') + '/'
                    except:
                        continue
                    else:
                        yield Request(url)
        yield Request(self.start_urls[0])

    def parse(self, response):
        if ('temporarilyUnavailable' in response.url) and ('redirect_urls' in response.meta) and (response.meta['redirect_urls']):
            url = response.meta['redirect_urls'][0]
            yield Request(url, dont_filter=True)
            return

        urls = response.xpath('//nav[@id="category-navigation"]//a/@href').extract()
        for url in map(lambda u: response.urljoin(u), urls):
            yield Request(url)

        urls_all = response.xpath('//span[@class="class-type-more"]/a/@href').extract()
        for url in map(lambda u: response.urljoin(u), urls_all):
            yield Request(url)

        if not urls_all:
            pages = set(response.xpath('//div[@class="pagination-container"]//li[@class="next"]/a/@href').extract())
            for url in map(lambda u: response.urljoin(u), pages):
                yield Request(url)

            products = response.xpath('//div[@class="products"]/div[@class="product" and div[contains(@class, "cart")]]')
            for product in products:
                product_name = ' '.join(product.xpath('.//h3[contains(@class, "name")]//text()').extract())
                product_url = map(lambda u: response.urljoin(u), product.xpath('.//h3[contains(@class, "name")]/a/@href').extract())[0]
                product_price = product.xpath('.//div[@class="product-price"]/span[@class="price"]/text()').extract()[0]
                product_image = map(lambda u: response.urljoin(u), product.xpath('.//div[@class="product-image"]//img/@data-echo').extract())[0]
                product_sku = filter(lambda l: l.strip(), product_url.split('/'))[-1]
                product_brand = product.xpath('.//h3[contains(@class, "name")]//text()').extract()[0]
                product_identifier = '%s-%s' % (product_brand.strip(), product_sku.strip())
                product_category = response.xpath('//div[@class="breadcrumb-inner"]//li//span[@itemprop="title"]/text()').extract()

                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('name', product_name)
                loader.add_value('url', product_url)
                loader.add_value('price', product_price)
                loader.add_value('image_url', product_image)
                loader.add_value('sku', product_sku)
                loader.add_value('brand', product_brand)
                loader.add_value('identifier', product_identifier)
                loader.add_value('category', product_category)

                item = loader.load_item()
                if item['identifier'] not in self._identifier_name:
                    self._identifier_name[item['identifier']] = item['name']
                else:
                    item['name'] = self._identifier_name[item['identifier']]

                yield item

            if not products:
                urls = response.xpath('//h3[@class="name"]/a/@href').extract()
                for url in map(lambda u: response.urljoin(u), urls):
                    yield Request(url)

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        return 'temporarilyUnavailable' in response.url
