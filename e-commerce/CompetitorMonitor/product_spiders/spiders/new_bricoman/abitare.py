import re
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class AbitareSpider(BaseSpider):
    name = 'newbricoman-abitare.com'
    allowed_domains = ['abitare.com']
    start_urls = ['http://www.abitare.com']

    def start_requests(self):
        urls = ('http://www.abitare.com', 'http://abitare.com/prodotti.aspx')
        for url in urls:
            yield Request(url, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="div_banda_categorie"]//a')
        categories += hxs.select('//div[@id="div_elenco_cat_lato"]//a[not(contains(@href,"javascript"))]')
        for category in categories:
            url = category.select('./@href')[0].extract()
            cat_name = category.select('./@title')[0].extract()
            yield Request(urljoin_rfc(base_url, url), meta={'category': cat_name})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//a[contains(text(),"Avanti")]/@href').re('\(\'(.*?)\'')
        if next_page:
            yield FormRequest.from_response(response, formdata={'__EVENTTARGET': next_page[0]}, meta=response.meta)

        products = hxs.select('//div[contains(@class,"div_tit_prod_ele")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        base_url = get_base_url(response)

        product_id = response.url.split('/')[-1]

        name = hxs.select('//span[@id="cp_corpo_lbl_titolo"]/text()').extract()

        if not name:
            return

        product_loader = ProductLoader(item=Product(), selector=hxs)

        product_loader.add_value('name', u'{}'.format(name[0].strip().title()))

        product_loader.add_value('url', response.url)

        brand = hxs.select('//span[@id="cp_corpo_lbl_produttore"]/text()').extract()
        product_loader.add_value('brand', brand[0].title())

        product_loader.add_value('category', response.meta.get('category', '').title())

        product_loader.add_value('identifier', product_id)

        sku = hxs.select('//span[@id="cp_corpo_lbl_modello"]/text()').extract()
        if sku:
            product_loader.add_value('sku', sku[0])

        image_url = hxs.select('//img[@id="cp_corpo_img_dettaglio"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            product_loader.add_value('image_url', image_url)

        price = hxs.select('//span[@id="cp_corpo_lbl_prezzo"]/text()').extract()
        product_loader.add_value('price', price[0].replace('.', '').replace(',', '.') if price else '0.00')

        if not product_loader.get_output_value('price'):
            product_loader.add_value('stock', 0)

        yield product_loader.load_item()
