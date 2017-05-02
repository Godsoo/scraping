"""
Account: Tiger Chef
Name: tigerchef.com
"""


from scrapy import Spider, Request
from product_spiders.items import Product
from tigerchefloader import TigerChefLoader as ProductLoader

from tigerchefitems import TigerChefMeta


class TigerChefSpider(Spider):
    name = 'tigerchef.com'
    allowed_domains = ['tigerchef.com']
    start_urls = ('http://www.tigerchef.com/sitemap.php',)

    def parse(self, response):
        categories = response.xpath('//div[@class="sitemap"]//a/@href').extract()
        categories += response.xpath('//*[@id="nav"]//li/a/@href').extract()
        categories += response.xpath('//ul[@class="cl_subs"]//a/@href').extract()
        categories += response.xpath('//div[@class="product-box"]//a/@href').extract()
        categories += response.xpath('//div[@class="store-box"]//a/@href').extract()
        categories += response.xpath('//div[@class="store-cat-box-content"]//a/@href').extract()

        for category in categories:
            category_url = response.urljoin(category)
            yield Request(category_url)

        product_urls = response.xpath('//div[starts-with(@id, "product_")]//strong[@class="category-title"]//a/@href').extract()
        for url in product_urls:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//a[@rel="next"]/@href').extract()
        for url in next_page:
            yield Request(response.urljoin(next_page[0]))

        data_found = bool(categories) or bool(product_urls)
        if (not data_found) and (response.meta.get('retries', 0) < 3):
            yield Request(response.url, dont_filter=True,
                          meta={'retries': response.meta.get('retries', 0) + 1})

    def parse_product(self, response):
        itemno = response.xpath('//div[@id="product-main-info"]//a[contains(@id, '
                                '"wishlist_link_")]/@id').re(r'(\d+)')
        if not itemno:
            self.log('ERROR: itemno not found => %s' % response.url)
            return
        else:
            itemno = itemno[0]

        price = ''.join(response.xpath('//span[@id="the-price"]//text()').re(r'[\d\.,]+')[-2:])
        if not price:
            self.log('WARNING: price not found => %s' % response.url)
            price = '0.00'

        sku = response.xpath('//li[@itemprop="sku"]/text()').extract()
        if not sku:
            self.log('WARNING: SKU not found => %s' % response.url)
        else:
            sku = sku[0].replace('Model #:', '').strip()

        brand = response.xpath('//li[@itemprop="name"]/text()').extract()
        image_url = response.xpath('//div[@id="zoom-div"]//img[@itemprop="image"]/@src').extract()
        category = response.xpath('//span[@class="breadcrumb-element"]'
                                  '//*[@itemprop="name"]/text()').extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]//text()')
        loader.add_value('price', price)
        if sku:
            loader.add_value('sku', sku)
        if image_url:
            loader.add_value('image_url', image_url)
        if brand:
            loader.add_value('brand', brand)
        loader.add_value('identifier', itemno + ' ' + sku)
        if category:
            loader.add_value('category', category[0].strip())

        product = loader.load_item()

        sold_as = response.xpath('//li[contains(text(),"Sold As:")]/../li[2]/text()')\
                          .extract()[0].strip()
        metadata = TigerChefMeta()
        metadata['sold_as'] = sold_as
        product['metadata'] = metadata

        yield product
