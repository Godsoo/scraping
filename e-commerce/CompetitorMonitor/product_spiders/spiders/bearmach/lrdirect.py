"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5141
"""

import os
import csv
import paramiko

from scrapy.spiders import Spider
from scrapy.http import FormRequest, Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class LRDirect(Spider):
    name = 'bearmach-lrdirect'
    allowed_domains = ['lrdirect.com']
    
    cookies = {'GlobalE_Data': '%7B%22countryISO%22%3A%22GB%22%2C%22currencyCode%22%3A%22GBP%22%2C%22cultureCode%22%3A%22en-GB%22%7D'}
    
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
            for row in reader:
                allmakes_sku = row['Allmakes Part Number'].strip()
                britpart_sku = row['Britpart Part Number'].strip()

                brands = ['ALLMAKES', 'BRITPART']
                brands.append(row['Allmakes Brand'].upper().strip())
                brands.append(row['Britpart Brand'].upper().strip())

                if allmakes_sku == britpart_sku:
                    yield FormRequest(
                        'https://www.lrdirect.com/search_category.php',
                        self.parse_search_results,
                        formdata={'posted_data[substring]': allmakes_sku},
                        cookies=self.cookies,
                        meta={'sku': allmakes_sku, 'brand': row['Allmakes Brand'].decode('latin-1').strip(), 'brands': brands})
                else:
                    if allmakes_sku:
                        yield FormRequest(
                            'https://www.lrdirect.com/search_category.php',
                            self.parse_search_results,
                            formdata={'posted_data[substring]': allmakes_sku},
                            cookies=self.cookies,
                            meta={'sku': allmakes_sku, 'brand': row['Allmakes Brand'].decode('latin-1').strip(), 'brands': brands})

                    if britpart_sku:
                        yield FormRequest(
                            'https://www.lrdirect.com/search_category.php',
                            self.parse_search_results,
                            formdata={'posted_data[substring]': britpart_sku},
                            cookies=self.cookies,
                            meta={'sku': britpart_sku, 'brand': row['Britpart Brand'].decode('latin-1').strip(), 'brands': brands})
                
    def parse_search_results(self, response):
        sku = response.meta['sku']
        brands = response.meta['brands']

        for product in response.css('.item .details'):
            product_brand = product.css('a.product-title::text').re('Brand:[\r\n ]*(.+)')[0].strip().upper()
            if product_brand == 'ORIGINAL EQUIPMENT':
                product_brand = 'OEM'

            product_sku = product.xpath('.//a[@class="sku-value"]/text()').extract()
            product_sku = product_sku[0].strip() if product_sku else ''

            if product_brand.upper().strip() in brands and product_sku and product_sku.upper().startswith(sku.upper()):
                yield Request(product.css('a.product-title::attr(href)').extract_first(), 
                              self.parse_product, meta=response.meta)

    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        loader.add_xpath('identifier', '//input[@name="productid"]/@value')
        loader.add_value('url', response.url)
        loader.add_css('name', '.descr::text')
        loader.add_css('price', 'span.currency::text')
        loader.add_value('sku', response.meta['sku'])
        image_url = response.css('img#product_thumbnail::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('brand', response.meta['brand'])
        stock = response.css('.quantity script::text').re('product_avail = (\d+);')[0]
        loader.add_value('stock', stock)
        item = loader.load_item()
        if stock == '0':
            yield item
            return
        request = FormRequest.from_response(response, 
                                            formname='orderform', 
                                            meta={'cookiejar': item['identifier'],
                                                  'item': Product(item)}, 
                                            cookies=self.cookies,
                                            callback=self.parse_shipping,
                                            dont_filter=True)
        yield request
        
    def parse_shipping(self, response):
        shipping_costs = response.css('.checkout-shippings').xpath('.//span[not(contains(., "Collect"))]/span/text()').extract()
        shipping_costs = [extract_price(cost) for cost in shipping_costs]
        item = response.meta['item']
        item['shipping_cost'] = min(shipping_costs)
        yield item
