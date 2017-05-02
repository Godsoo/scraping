from urlparse import urljoin

import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy import log
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price


class YMeta(Item):
    promotions = Field()

class TheBodyshopFrSpider(BaseSpider):
    name = 'thebodyshop_fr'
    allowed_domains = ['thebodyshop.fr']
    start_urls = [
        'http://www.thebodyshop.fr/corps-bain/beurres-corporels/beurre-corporel-karite.aspx',
        'http://www.thebodyshop.fr/best-sellers/hommes/creme-protectrice-mains-chanvre.aspx',
        'http://www.thebodyshop.fr/corps-bain/gels-douche/gel-douche-fraise.aspx',
        'http://www.thebodyshop.fr/parfums/best-sellers/eau-de-toilette-white-musk.aspx',
        'http://www.thebodyshop.fr/parfums/pour-elle/eau-de-toilette-jasmin-de-nuit-dinde.aspx',
        'http://www.thebodyshop.fr/maquillage/levres/rouge-a-levres-colour-crush-rouge.aspx',
        'http://www.thebodyshop.fr/maquillage/nouveau-bb-cream/bb-cream-all-in-one.aspx',
        'http://www.thebodyshop.fr/best-sellers/soin-du-visage/creme-de-jour-hydratante-vitamine-e.aspx',
        'http://www.thebodyshop.fr/visage/best-sellers/revelateur-de-jeunesse-drops-of-youth.aspx',
        'http://www.thebodyshop.fr/visage/hommes/creme-protectrice-visage-tonifiante-racine-de-maca-hommes.aspx',
    ]
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        price = 0
        stock = 0
        tmp = None
        tmp = hxs.select('//ul[@class="size-selector"]//label[1]/@data-weight').extract()
        if tmp:
            if response.url in ['http://www.thebodyshop.fr/parfums/best-sellers/eau-de-toilette-white-musk.aspx', ]:
                dd = tmp[1].split('#')
            else:
                dd = tmp[0].split('#')
            loader.add_value('identifier', dd[4])
            loader.add_value('sku', dd[4])
            price = extract_price(dd[5])
            loader.add_value('price', price)
        else:
            sku = ''.join(hxs.select("//div[@data-sku]/@data-sku").extract())
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            price = extract_price(''.join(
                hxs.select("//div[@data-sku]//p[contains(concat('',@class,''), 'price ')]//text()").extract()
            ))
            loader.add_value('price', price)
        name = ''
        tmp = hxs.select('//h1[@class="title"]/@title').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        # stock
        if price:
            stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//img[@class="product"]/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0].strip())
            loader.add_value('image_url', url)
        #brand
        loader.add_value('brand', 'THE BODY SHOP')
        #category
        tmp = hxs.select('//nav[@id="breadcrumb_product"]/ul/li/a/text()').extract()
        if len(tmp) > 1:
            for s in tmp[1:]:
                loader.add_value('category', s)
        #shipping_cost
        if price < 40:
           loader.add_value('shipping_cost', 5.95)

        product = loader.load_item()
        metadata = {}
        tmp = hxs.select("//div[@id='product-offers']/p[2]//text()").extract()
        product['metadata'] = ' '.join([x.strip() for x in tmp if x.strip()])

        return product