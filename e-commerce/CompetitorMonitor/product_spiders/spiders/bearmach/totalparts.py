"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5141
"""

import re
import os
import csv
import paramiko

from scrapy.spiders import Spider
from scrapy.http import FormRequest, Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class TotalpartsSpider(Spider):
    name = 'bearmach-totalparts.co.uk'
    allowed_domains = ['totalparts.co.uk']

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "8PskJYFa"
        username = "bearmach"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        file_path = os.path.join(HERE, 'bearmach_products.csv')
        sftp.get('bearmach_feed.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            search_url = 'http://www.totalparts.co.uk/search/for/%s/'
            for row in reader:
                allmakes_sku = row['Allmakes Part Number'].strip()
                britpart_sku = row['Britpart Part Number'].strip()

                brands = ['ALLMAKES', 'BRITPART']
                brands.append(row['Allmakes Brand'].upper().strip())
                brands.append(row['Britpart Brand'].upper().strip())

                if allmakes_sku == britpart_sku:
                    yield Request(search_url % allmakes_sku,
                                  self.parse_search_results,
                                  meta={'sku': allmakes_sku, 'brand': row['Allmakes Brand'].decode('latin-1'), 'brands': brands})
                else:
                    if allmakes_sku:
                        yield Request(search_url % allmakes_sku, callback=self.parse_search_results,
                                      meta={'sku': allmakes_sku, 'brand': row['Allmakes Brand'].decode('latin-1'), 'brands': brands})

                    if britpart_sku:
                        yield Request(search_url % britpart_sku, callback=self.parse_search_results,
                                      meta={'sku': britpart_sku, 'brand': row['Britpart Brand'].decode('latin-1'), 'brands': brands})
                
    def parse_search_results(self, response):
        sku = response.meta['sku']
        brands = response.meta['brands']
        products = response.xpath('//div[@id="product_list_inner"]//tr/td[contains(p/text(), "Part No")]')
        for product in products:
            product_code = product.xpath('p/text()').re('Part No: (.*) - Brand')[0]
            product_brand = product.xpath('p/text()').re('Brand: (.*) -  Supplier')[0].strip()

            if product_code.upper() == sku.upper() and product_brand.upper() in brands:
                url = response.urljoin(product.xpath('p/a/@href').extract()[0])
                meta = response.meta
                meta['product_brand'] = product_brand
                yield Request(url, self.parse_product, meta=meta)

        if not products:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        sku = response.meta['sku']
        brands = response.meta['brands']

        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//input[@name="pid"]/@value').extract()
        if identifier:
            product_brand = response.meta.get('product_brand', None)
            if not product_brand:
                product_brand = re.findall('BRAND:</b>&nbsp; (.*)<br><b>W', response.body)
                if product_brand:
                    product_brand = product_brand[0].strip()
                else:
                    self.log('>>> ERROR: No brand found: ' + response.url)
                    return
                product_code = response.xpath('//span[@itemprop="name"]/text()').re('(.*) : ')[0].strip()
                if product_brand.upper() not in brands or product_code.upper() != sku.upper():
                    return

            identifier = identifier[0]
            name = response.xpath('//span[@itemprop="name"]/text()').extract()[0].strip()
            price = response.xpath('//font[@class="selling_price"]/b/text()').extract()[0]

            loader.add_value('identifier', identifier)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('url', response.url)
            loader.add_value('sku', sku)
            image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
            if image_url:
                loader.add_value('image_url', response.urljoin(image_url[0]))

            loader.add_value('brand', product_brand)

            weight = response.xpath('//p[b[contains(text(), "Weight or Volume")]]/span/text()').extract()
            if weight:
                weight = weight[0].upper()
                # convert price to grams if it is in KG
                if 'KG' in weight:
                    weight = extract_price(weight) * 1000
                else:
                    weight = extract_price(weight)
                if weight > 1000:
                    loader.add_value('shipping_cost', 4.99)
                else:
                    loader.add_value('shipping_cost', 3.50)

            item = loader.load_item()
            yield item

