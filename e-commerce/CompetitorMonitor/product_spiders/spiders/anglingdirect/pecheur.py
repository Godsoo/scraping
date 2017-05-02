import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class PecheurSpider(BaseSpider):
    name = 'angling_direct-pecheur.com'
    allowed_domains = ['pecheur.com']
    start_urls = ('http://www.pecheur.com/en/gb',)

    def start_requests(self):
        urls = ('http://www.pecheur.com/en/gb/sell-fishing-1,0,0,0.html',
                'http://www.pecheur.com/en/gb/sell-camping-outdoor-activities-2883,0,0,0.html',
                'http://www.pecheur.com/en/gb/sell-clothing-1674,0,0,0.html')
        for url in urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = hxs.select('//div[@class="colonne_gauche"]/div[@id="menu"]//ul/li/a/@href').extract()
        for cat in cats:
            cat = cat.replace('0.html', '1.html') # Sort by name
            yield Request(urljoin_rfc(base_url, cat))

        next_page = hxs.select('//div[@class="droite"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//li[@class="article"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        identifier = re.search('-([\d\,]+)\.html', response.url).group(1)
        product_name = hxs.select('//div[@itemprop="name"]/text()')[0].extract().strip()
        base_price = hxs.select('//p[@itemprop="Price"]/text()')[0].extract()
        base_price_decimal = hxs.select('//p[@itemprop="Price"]/span[@class="decimal"]/text()').extract()
        if base_price_decimal:
            base_price += base_price_decimal[0]
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        category = hxs.select('//div[@id="filCateg"]/a/text()').extract()
        brand = hxs.select('//span[@itemprop="brand"]/text()')[0].extract().strip()
        out_of_stock = hxs.select('//img[@id="BoutonIndispo"]')

        models = hxs.select('//table[@class="tabModeles"]/tr[@class="tr_FA"]')
        for model in enumerate(models):
            i = str(model[0])
            model = model[1]

            model_name = model.select('.//td[@class="ref"]/text()')[0].extract().strip()
            model_price = model.select('.//td[@class="prix"]/span[@class="Normal" or @class="NormalSansCoupon" or @class="Promo" or @class="TopPrix"]/text()')[0].extract()
            model_price_decimal = model.select('.//td[@class="prix"]/span[@class="Normal" or @class="NormalSansCoupon" or @class="Promo" or @class="TopPrix"]/span[@class="decimal"]/text()').extract()
            if model_price_decimal:
                model_price += model_price_decimal[0]

            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', '{}.{}'.format(identifier, i))
            loader.add_value('sku', model_name)
            loader.add_value('url', response.url)
            loader.add_value('name', u'{} {}'.format(product_name, model_name))
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            loader.add_value('brand', brand)
            loader.add_value('category', category[-1] if category else '')
            loader.add_value('price', model_price)
            if out_of_stock:
                loader.add_value('stock', 0)

            yield loader.load_item()

        if not models:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', identifier)
            loader.add_value('url', response.url)
            loader.add_value('name', product_name)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            loader.add_value('brand', brand)
            loader.add_value('category', category[-1] if category else '')
            loader.add_value('price', base_price)
            if out_of_stock:
                loader.add_value('stock', 0)

            yield loader.load_item()
