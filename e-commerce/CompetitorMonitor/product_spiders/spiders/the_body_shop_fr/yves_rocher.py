from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price


class YMeta(Item):
    promotions = Field()

class YvesrocherSpider(BaseSpider):
    name = 'thebodyshop-yves-rocher.fr'
    allowed_domains = ['yves-rocher.fr']
    start_urls = [
        'http://www.yves-rocher.fr/corps-et-solaire/soin-du-corps/soin-nutrition-et-reparation/concentre-ultra-reparateur/p/yr.R63620',
        'http://www.yves-rocher.fr/corps-et-solaire/soin-du-corps/soin-des-mains/creme-mains-anti-rides-haute-nutrition/p/yr.R78259',
        'http://www.yves-rocher.fr/bain-e-douche/envie-de%E2%80%A6/energie/gel-douche-energisant-pamplemousse-de-floride/p/yr.R03413',
        'http://www.yves-rocher.fr/parfum/parfum-feminin/eau-fraiche/flowerparty-yves-rocher---%3C-br%3El-eau-de-toilette-30ml/p/yr.R22061',
        'http://www.yves-rocher.fr/parfum/parfum-feminin/eau-fraiche/nature---eau-de-toilette-60ml/p/yr.R88436',
        'http://www.yves-rocher.fr/maquillage/levres/rouge-a-levres/rouge-a-levres/p/yr.R44557',
        'http://www.yves-rocher.fr/maquillage/teint/fond-de-teint-et-bb-creme/bb-creme-sublimatrice-6-en-1/p/yr.R10689',
        'http://www.yves-rocher.fr/soin-visage/soin-par-type-de-peau/peaux-normales-a-mixtes/creme-riche-hydratation-intense-24h/p/yr.R34364',
        'http://www.yves-rocher.fr/soin-visage/soin-par-type-de-peau/tous-types-de-peau/serum-intensificateur-jeunesse/p/yr.R18705',
        'http://www.yves-rocher.fr/soin-visage/soin-homme/soin-visage/soin-hydratant-3-en-1-peaux-sensibles/p/yr.R88964',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        sku = response.url.split('R')[-1]
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)

        loader.add_xpath('name', "//div[@id='id_productCommerceInfoDiv']//h1//text()")
        #price
        price_text = ''.join(hxs.select("//div[@id='id_productCommerceInfoDiv']//div[@class='price']/text()").extract())
        price = extract_price(price_text)
        loader.add_value('price', price)
        #stock
        stock = 1
        if hxs.select("//div[@id='panierAdd']/button[@style]"):
            stock = 0
        loader.add_value('stock', stock)
        #image_url
        loader.add_xpath('image_url', "//img[@id='product_slider_image']/@src")
        #brand
        loader.add_xpath('brand', "(//a[@title='@YR'])[1]//text()")
        #category
        loader.add_xpath('category', "//div[@class='crumbs']/span[position() > 1 and position() < last()]//text()")
        #shipping_cost
        if price <= 4:
            loader.add_value('shipping_cost', Decimal(6.8))
        else:
            loader.add_value('shipping_cost', Decimal(4))

        product = loader.load_item()
        metadata = YMeta()
        tmp = hxs.select("//div[@id='id_productCommerceInfoDiv']//div[@class='badge hse cross']//img/@alt").extract()
        if tmp:
            metadata['promotions'] = []
            for s in tmp:
                metadata['promotions'].append(s)
            metadata['promotions'] = ','.join(metadata['promotions'])
        if metadata:
            product['metadata'] = metadata

        return product

