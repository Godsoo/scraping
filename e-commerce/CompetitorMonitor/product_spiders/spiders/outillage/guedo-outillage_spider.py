import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

from scrapy.http import FormRequest
from product_spiders.utils import extract_price_eu


class guedo_outillage_spider(BaseSpider):
    name = 'guedo-outillage.fr'
    allowed_domains = ['guedo-outillage.fr', 'www.guedo-outillage.fr']
    start_urls = (
        'http://www.guedo-outillage.fr/perceuse-visseuse-uni_fr_11.html',
        'http://www.guedo-outillage.fr/perforateur-burineur-uni_fr_12.html',
        'http://www.guedo-outillage.fr/meuleuse-ponceuse-uni_fr_13.html',
        'http://www.guedo-outillage.fr/rabot-defonceuse-uni_fr_16.html',
        'http://www.guedo-outillage.fr/scie-portative-stationnaire-uni_fr_15.html',
        'http://www.guedo-outillage.fr/mesure-controle-uni_fr_8.html',
        'http://www.guedo-outillage.fr/pompe-groupe-uni_fr_14.html',
        'http://www.guedo-outillage.fr/foret-jardin-uni_fr_17.html',
        'http://www.guedo-outillage.fr/outillage-a-main-uni_fr_9.html',
        'http://www.guedo-outillage.fr/protection-habillement-uni_fr_10.html',
        'http://www.guedo-outillage.fr/pack-outils-uni_fr_18.html',
        'http://www.guedo-outillage.fr/accessoire-consommable-uni_fr_7.html',
    )

    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[contains(@class, "listing_rubriques")]/div//h2/a/@href').extract()
        for url in categories:
            url = url + '?page_number=1'
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)


    def parse_category(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class, "listing_produits")]/div//h2/a/@href').extract()
        for url in products:
            url = 'http://www.guedo-outillage.fr/' + url
            yield Request(url, callback=self.parse_product)

        if products:
            page_number = re.findall(re.compile("page_number=(\d*)"), response.url)[0]
            page_number = '?page_number=' + str(int(page_number) + 1)
            next_page = re.sub("\?page_number=\d*", page_number, response.url)
            yield Request(next_page, callback=self.parse_category)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        identifier = hxs.select('//input[@name="product_id"]/@value').extract()[0]
        sku = hxs.select('//div[@class="texte_zoom"]/div/div/h2/text()').extract()[0]
        category = hxs.select('//div[@class="breadParent"]/ol/li/a/span/text()').extract()[1:]
        name = hxs.select('//h1/span/text()').extract()[0].strip()
        brand = hxs.select('//div[@class="texte_zoom"]/div/div/a/img/@alt').extract()
        price = "".join(hxs.select('//div[@id="prixZoom"]//div[@class="ttc"]/span[@itemprop="price"]/span/text()').extract()).strip().replace(' ', '')
        image_url = hxs.select('//div[@class="photos"]//img[@itemprop="image"]/@src').extract()
        stock = hxs.select('//div[contains(@name,"dispodiv")]/span[contains(text(),"En stock")]')

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_value('name', name)
        l.add_value('category', category)
        if brand:
            l.add_value('brand', brand)
        l.add_value('sku', sku)
        l.add_value('url', response.url)
        l.add_value('price', extract_price_eu(price))
        # if not stock:
        l.add_value('stock', 1)
        if image_url:
            l.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0].strip()))
        yield l.load_item()
