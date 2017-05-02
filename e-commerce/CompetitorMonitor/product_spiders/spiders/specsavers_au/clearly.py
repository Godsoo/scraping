# -*- coding: utf-8 -*-


"""
Account: SpecSavers AU
Name: specsavers_au-clearly.com.au
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4568
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.items import (
    ProductLoaderWithNameStrip as ProductLoader,
    Product,
)
from extruct.w3cmicrodata import MicrodataExtractor

from specsaversitems import SpecSaversMeta


class ClearlyComAu(Spider):
    name = 'specsavers_au-clearly.com.au'
    allowed_domains = ['clearly.com.au']

    start_urls = ['http://www.clearly.com.au/catalog/view-all-products-by-name']

    def parse(self, response):
        for val in response.xpath('//select[@id="productCategory"]/option/@value').extract()[1:]:
            url = add_or_replace_parameter(response.url, 'productCategory', val)
            yield Request(url)
        product_urls = response.xpath('//div[@id="view-all-product-content"]//a/@href').extract()
        for url in product_urls:
            yield Request(response.urljoin(url),
                          callback=self.parse_product)

    def parse_product(self, response):
        mde = MicrodataExtractor()
        data = mde.extract(response.body)

        product_data = data['items'][1]['properties']

        extra_data = {}
        for l in response.body.split('\n'):
            if 'vgoogle_ecommProd' in l:
                line_data = l.strip()
                key = line_data.split(':')[0].strip().replace('vgoogle_ecommProd', '')
                value = line_data.split(':')[1][3:-3]
                if key not in extra_data:
                    extra_data[key] = value

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', product_data.get('sku', extra_data['ID']))
        loader.add_value('sku', product_data.get('sku', extra_data['ID']))
        loader.add_value('name', product_data.get('name', extra_data['Name']))
        loader.add_value('url', response.url)
        if 'price' in product_data:
            loader.add_value('price', product_data['price'])
        elif 'Price' in extra_data:
            loader.add_value('price', extra_data['Price'])
        else:
            price = response.xpath('//*[(contains(@class, "product-item") and '
                                   'contains(@class, "product-price")) or @id="price-amount"]//text()')\
                            .re(r'[\d\.,]+')
            loader.add_value('price', price)
        try:
            loader.add_value('category',
                             data['items'][0]['properties']['itemListElement']
                             [1]['properties']['name'])
        except:
            loader.add_value('category', extra_data['Cat'])
        loader.add_value('brand', product_data.get('manufacturer', extra_data['Brand']))
        try:
            loader.add_value('image_url',
                response.urljoin(response.xpath('//div[@id="prod-img-placehold"]/img/@srcset')
                                 .re(r'(.*\.jpg)')[0].split(',')[-1].strip()))
        except:
            pass

        item = loader.load_item()
        metadata = SpecSaversMeta()
        promotional_data = response.xpath('//div[@class="arrow-container"]/div/text()').extract()
        metadata['promotion'] = promotional_data[0].strip() if promotional_data else ''
        item['metadata'] = metadata
        yield item
