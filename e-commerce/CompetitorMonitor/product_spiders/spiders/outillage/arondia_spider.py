import re

# from scrapy.spider import BaseSpider
from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from productloader import load_product
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader

from product_spiders.utils import remove_punctuation_and_spaces


class arondia_spider(SitemapSpider):
    name = 'arondia.com'
    allowed_domains = ['arondia.com']
    start_urls = ('http://www.arondia.com',)
    sitemap_urls = ('http://www.arondia.com/sitemap.xml',)

    sitemap_rules = [
        ('/', 'parse_product'),
    ]

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        pages = hxs.select('//select[@name="nbPagesPerPage"]')
        cat_text = hxs.select('//h2[@class="titre_image titre_image_niv1"]')
        if not pages and not cat_text:
            try:
                category = hxs.select('//div[@id="chemin_os"]//a/span[@itemprop="title"]/text()').extract()[-1]
            except:
                category = None

            main_ref = hxs.select('//div[@id="ficheProduitPied"]//span[@class="reference"]/text()').re(r'R\xe9f. (.*)')
            name = response.xpath('//div[@id="ficheProduitPied"]/div[@id="fichetitre"]/text()').extract()
            if not name or (name and not name[0].strip()):
                name = response.xpath('//span[@itemprop="name"]/text()').extract()
            price = ''.join(response.xpath('//div[@id="ficheProduitPied"]//*[@class="prix"]/text()').re('\S+'))
            if name:
                identifier = remove_punctuation_and_spaces(name[0]).lower()
                image_url = response.xpath('//div[@id="ficheProduitPied"]//img/@src').extract()
                image_url = urljoin_rfc(get_base_url(response), image_url[0]) if image_url else ''
                
                l = ProductLoader(item=Product(), selector=response.xpath('//div[@id="ficheProduitPied"]'))
                l.add_value('identifier', identifier)
                l.add_value('name', name)
                if category:
                    l.add_value('category', category)
                l.add_xpath('sku', '//div[@id="ligne_achat"]//text()', re=':(.+)')
                l.add_value('stock', 1)
                l.add_value('url', response.url)
                l.add_value('price', price)
                l.add_value('image_url', image_url)
                yield l.load_item()

            products = hxs.select('//div[@id="bloc_offre"]/div/div[@class="bloc_cadre_pied"]/form[@class="mini_fiche_ligne"]')
            products += hxs.select('//div[@id="bloc_accessoire"]/div/div[@class="bloc_cadre_pied"]/form[@class="mini_fiche_ligne"]')
            for p in products:
                p_url = p.select('.//div[@class="ligne_titre"]/a/@href').extract()
                if p_url:
                    yield Request(urljoin_rfc(get_base_url(response), p_url[0]), callback=self.parse_product)
                    continue
                name = p.select('.//div[@class="colonne_1"]/div[@class="ligne_titre"]/span[@class="titre_descriptif"]/strong/text()')
                if not name:
                    name = p.select('.//div[@class="colonne_1"]/div[@class="ligne_titre"]/a/span[@class="titre_descriptif"]/strong/text()')
                name = name[0].extract().strip()
                name = name.replace('- OFFRE SPECIALE !', '').strip()
                url = response.url
                price = "".join(p.select('.//div[@class="lignebeige"]/div[@class="wrapperPrix"]/div/div/div/b/text()').re(r'([0-9\,\. ]+)')).strip()
                # identifier = p.select('.//div/div/span[@class="reference"]/text()').extract()[1].strip()
                identifier = remove_punctuation_and_spaces(name).lower()
                image_url = p.select('.//div/img/@src').extract()
                if image_url:
                    image_url = urljoin_rfc(get_base_url(response), image_url[0])
                sku = ''
                p_ref = p.select('.//span[@class="reference"]//text()').re(r'(\d+)')
                if main_ref and p_ref:
                    if p_ref[0] == main_ref[0]:
                        p_sku = p.select('//div[@id="ligne_achat"]/table/tr/td/text()').extract()
                        if p_sku:
                            try:
                                sku = p_sku[0].strip().split(': ')[1]
                            except IndexError:
                                sku = p.select('//div[@id="ligne_achat"]/table/tr/td/text()').re('\S+')[2]

                l = ProductLoader(item=Product(), response=response)
                l.add_value('identifier', identifier)
                l.add_value('name', name)
                if category:
                    l.add_value('category', category)
                l.add_value('sku', sku)
                l.add_value('stock', 1)
                l.add_value('url', url)
                l.add_value('price', price)
                l.add_value('image_url', image_url)
                yield l.load_item()

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(response)

        # brands
        brands = hxs.select("//select[@id='rechercheCriteresForm_liste']//option/@value").extract()
        for url in brands:
            yield Request(urljoin_rfc(base_url, url))

        # categories
        category_urls = hxs.select('//div[@id="menu_produit"]/ul/li/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin_rfc(base_url, url))

        # subcategories
        subcategory_urls = hxs.select('//ul[@id="famille_liste_es"]/li/a/@href').extract()
        for suburl in subcategory_urls:
            yield Request(urljoin_rfc(base_url, suburl))

        # subsubcats
        subsubcat_urls = hxs.select('//div[@class="bloc_cadre bloc_modele2"]/div/div/form/div/div[@class="ligne_titre"]/a/@href').extract()
        for subsuburl in subsubcat_urls:
            # category = hxs.select('//div[@id="contenu_sc"]/div/h1/text()').extract()
            yield Request(urljoin_rfc(base_url, subsuburl))

        # next page
        next_pages = hxs.select('//form[@id="formPageHaut"]/a/@href').extract()
        if next_pages:
            for page in next_pages:
                yield Request(urljoin_rfc(base_url, page))

        # products
        for p in self.parse_product(response):
            yield p
