import json
from scrapy.spider import Spider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class WilshirewigsSpider(Spider):
    name = 'wilshirewigs'
    allowed_domains = ['wilshirewigs.com']
    start_urls = ['http://www.wilshirewigs.com']
    id_seen = []

    def parse(self, response):
        for url in response.xpath('//a[contains(span/text(), "Departments")]/following-sibling::ul//li/a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_products_list)
        for url in response.xpath('//a[span="Accessories"]/following-sibling::div//a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        links = response.xpath('//div[@class="category-products"]//h2/a/@href').extract()
        for link in links: ###
            url = link
            yield Request(url, callback=self.parse_product)

        next_page = response.xpath('//div[@class="pages"]//a[@title="Next"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]), callback=self.parse_products_list)

    def parse_product(self, response):
        json_data = None
        if 'new Product.OptionsPrice(' in response.body:
            d = response.body.split('new Product.OptionsPrice(',1)[1].split(');',1)[0]
            json_data = json.loads(d)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        sku = response.xpath('//input[@name="product"]/@value').extract()
        if sku:
            sku = sku[0]
        if json_data and json_data.get('productId',None):
            sku = json_data['productId']

        if not sku:
            self.log('WARNING: No product ID => %s' % response.url)
            return

        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')

        if json_data:
            price = str(json_data.get('productPrice',''))
        else:
            price = response.xpath('//span[@class="price"]/text()').extract()[0]

        if price:
            loader.add_value('price', price)
            loader.add_value('stock', 1)
        else:
            loader.add_value('price', '0.0')
            loader.add_value('stock', 0)

        image_url = response.xpath('//img[@id="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        brand = response.xpath('//div[@class="product-name"]/h2/a/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])

        categories = response.xpath('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        if len(categories) > 1:
            loader.add_value('category', categories[1:])

        product = loader.load_item()

        options = response.xpath('//ul[@id="color-swatch-attribute-92"]/li')
        if not options:
            if not product.get('identifier', None):
                self.log('WARNING: No product ID => %s' % response.url)
            else:
                if not product['identifier'] in self.id_seen:
                    self.id_seen.append(product['identifier'])
                    yield product
                else:
                    self.log('WARNING: Duplicate product ID => %s' % response.url)
            return

        # process options
        for sel in options:
            item = Product(product)
            opt_id = sel.xpath('@class').extract()
            if opt_id:
                item['identifier'] += '-' + opt_id[0].split()[0].split('-')[-1]
            opt_desc = filter(lambda s: s != '',
                              map(unicode.strip,
                                  sel.xpath('div[@class="tool-tip-description"]/text()')
                                  .extract()))
            if not opt_desc:
                opt_desc = filter(lambda s: s != '',
                                  map(unicode.strip,
                                      sel.xpath('div[@class="tool-tip-description"]/strong/text()')
                                      .extract()))
            if opt_desc:
                item['name'] = product['name'] + ' - ' + ''.join(opt_desc)

            if not item.get('identifier', None):
                self.log('WARNING: No product ID => %s' % response.url)
            else:
                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item
                else:
                    self.log('WARNING: Duplicate product ID => %s' % response.url)
