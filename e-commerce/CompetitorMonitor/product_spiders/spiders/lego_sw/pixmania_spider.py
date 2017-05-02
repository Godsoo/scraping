import copy
import json
import re

from scrapy import Spider, Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class PixmaniaSpider(Spider):
    name = "legosw-pixmania.com"
    allowed_domains = ['pixmania.se']
    search_url = 'https://www.pixmania.se/api/pcm/products?categoryId=m_448&page={page}&size={size}'
    product_url = 'https://www.pixmania.se/p/{brand_name}-{slug}-{id}?offerId={offer_id}'
    re_sku = re.compile('(\d{4,5})')

    def start_requests(self):
        url = self.search_url.format(page=0, size=10)
        yield Request(url, headers={'Language': 'se-SE'}, meta={'page': 0})

    def parse(self, response):
        data = json.loads(response.body)
        if data['hits']['hits']:
            page = response.meta.get('page', 0)
            yield Request(self.search_url.format(page=page+1, size=10))
        for p in data['hits']['hits']:
            p = p['_source']
            loader = ProductLoader(item=Product(), response=response)
            sku = self.re_sku.search(p['name'])
            if sku:
                loader.add_value('sku', sku.group(1))
            loader.add_value('image_url', p['default_image'])
            loader.add_value('name', p['name'])
            loader.add_value('identifier', p['external_id'])
            loader.add_value('brand', p['brand_name'])
            for cat in p['categories_names']:
                loader.add_value('category', cat)
            product = loader.load_item()
            for offer in [p['best_offer']] + p['other_offers']:
                item = copy.deepcopy(product)
                url = self.product_url.format(brand_name=p['brand_name'].lower(),
                                              slug=p['slug'],
                                              id=str(p['id']),
                                              offer_id=offer['id'])
                item['url'] = url
                item['price'] = offer['price_with_vat']
                dealer = offer['merchant']['name'].replace(u' SEse', u'')
                item['dealer'] = u'Pix - {}'.format(dealer)
                item['identifier'] += u'-{}'.format(dealer)
                if not offer['free_shipping']:
                    item['shipping_cost'] = offer['shipping_estimation']
                if offer['availability'] != 'in_stock':
                    item['stock'] = 0
                yield item
