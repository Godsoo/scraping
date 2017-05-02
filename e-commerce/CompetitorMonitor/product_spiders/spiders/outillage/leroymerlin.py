
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class LeroyMerlinSpider(BaseSpider):
    name = 'leroymerlin.fr'
    allowed_domains = ['leroymerlin.fr']

    start_urls = (
        'http://www.leroymerlin.fr/v3/p/produits/construction-menuiserie-l1308216916',
        'http://www.leroymerlin.fr/v3/p/produits/terrasse-jardin-l1308216920',
        'http://www.leroymerlin.fr/v3/p/produits/chauffage-plomberie-l1308216915',
        'http://www.leroymerlin.fr/v3/p/produits/outillage-l1308216921',
        'http://www.leroymerlin.fr/v3/p/produits/rangement-dressing/garage-atelier-buanderie-et-cave-l1308220643',
        'http://www.leroymerlin.fr/v3/p/produits/rangement-dressing/accessoires-de-rangement-l1400104992',
        'http://www.leroymerlin.fr/v3/p/produits/quincaillerie-securite/demenagement-manutention-et-transport-l1308217025',
        'http://www.leroymerlin.fr/v3/p/produits/quincaillerie-securite/etagere-et-rangement-utilitaire-l1308217024',
        'http://www.leroymerlin.fr/v3/p/produits/quincaillerie-securite/quincaillerie-exterieure-l1308217029',
        'http://www.leroymerlin.fr/v3/p/produits/carrelage-parquet-sol-souple-l1308216894',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for link in hxs.select('//section[contains(@class, "product-entry")]/ul//h3/a/@href').extract():
            url = urljoin_rfc(base_url, link)
            url = add_or_replace_parameter(url, 'sort', 'TRI_PAR_PRIX_CROISSANT_ID')
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        links = hxs.select('//section[contains(@class,"product-entry")]/ul/li//a[1]/@href').extract()
        if links:
            # This is a categories page.
            for link in links:
                url = urljoin_rfc(base_url, link)
                url = add_or_replace_parameter(url, 'sort', 'TRI_PAR_PRIX_CROISSANT_ID')
                yield Request(url, callback=self.parse_list)
            return

        products = hxs.select('//section[@id="showcase"]/div[@itemscope]')
        if not products:
            products = hxs.select('//section[@id="showcase"]/div[section[@class="prd-infos"] and figure]')
        if not products:
            products = hxs.select('//section[@id="showcase"]/div[contains(@class, "container-product")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            product_url = product.select('.//a[1]/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, product_url))
            product_loader.add_xpath('name', u'.//span[@itemprop="name"]/text()')
            product_loader.add_xpath('identifier', u'.//a[contains(@class, "prd-apercu")]/@data-reflm')
            product_loader.add_xpath('price',
                                     u'.//p[@class="price"]/strong/text()',
                                     lambda p: p.pop() if p else '0',
                                     re=r'([0-9\.]+)')
            product_loader.add_value('stock', 1)
            image = product.select(u'.//figure[@class="prd-visuel"]//a/noscript/img/@src').extract()
            if image:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image[0]))
            yield product_loader.load_item()

        next_page = hxs.select('//ul[@class="pagination"][1]/li/a[i/@class="ico-arrow-right"]/@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url, callback=self.parse_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//meta[@property="og:title"]/@content')
        product_loader.add_xpath('identifier', u'.//*[@id="global-reflm"]/span/text()')
        product_loader.add_xpath('price', '//article[@class="showcase-product"]//p[@class="price"]/strong/text()')
        product_loader.add_value('stock', 1)
        product_loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')

        item = product_loader.load_item()
        if item.get('identifier', ''):
            yield item
