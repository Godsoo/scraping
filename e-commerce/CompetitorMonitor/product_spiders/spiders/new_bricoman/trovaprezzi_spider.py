import os
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TrovaprezziSpider(BaseSpider):
    name = u'newbricoman-trovaprezzi.it'
    allowed_domains = [u'trovaprezzi.it']
    start_urls = ['http://www.trovaprezzi.it/prezzi_sicurezza-casa.aspx',
                  'http://www.trovaprezzi.it/prezzi_casalinghi.aspx',
                  'http://www.trovaprezzi.it/prezzi_pulizia-casa.aspx',
                  'http://www.trovaprezzi.it/prezzi_detersivi-pulenti.aspx',
                  'http://www.trovaprezzi.it/prezzi_arredo-bagno.aspx',
                  'http://www.trovaprezzi.it/prezzi_illuminazione.aspx',
                  'http://www.trovaprezzi.it/prezzi_giardinaggio.aspx',
                  'http://www.trovaprezzi.it/prezzi_arredamento-esterni.aspx',
                  'http://www.trovaprezzi.it/prezzi_barbecues-fornelli.aspx',
                  'http://www.trovaprezzi.it/prezzi_illuminazione-per-esterni.aspx',
                  'http://www.trovaprezzi.it/prezzi_energia-solare.aspx',
                  'http://www.trovaprezzi.it/prezzi_casette-e-garages.aspx',
                  'http://www.trovaprezzi.it/prezzi_sementi-concimi.aspx',
                  'http://www.trovaprezzi.it/prezzi_prodotti-agricoltura.aspx',
                  'http://www.trovaprezzi.it/prezzi_ferramenta.aspx',
                  'http://www.trovaprezzi.it/prezzi_elettroutensili.aspx',
                  'http://www.trovaprezzi.it/prezzi_elettronica-elettricita.aspx',
                  'http://www.trovaprezzi.it/prezzi_pile-e-batterie.aspx',
                  'http://www.trovaprezzi.it/prezzi_lampadine.aspx',
                  'http://www.trovaprezzi.it/prezzi_pittura.aspx',
                  'http://www.trovaprezzi.it/prezzi_supporti-accessori.aspx',
                  'http://www.trovaprezzi.it/prezzi_materiale-per-edilizia.aspx',
                  'http://www.trovaprezzi.it/prezzi_climatizzazione.aspx',
                  'http://www.trovaprezzi.it/prezzi_trattamento-aria.aspx',
                  'http://www.trovaprezzi.it/prezzi_elettrodomestici-riscaldamento.aspx',
                  'http://www.trovaprezzi.it/prezzi_stufe-riscaldamento.aspx',
                  'http://www.trovaprezzi.it/prezzi_cancelleria-ufficio.aspx',
                  'http://www.trovaprezzi.it/prezzi_imballaggio.aspx']

    download_delay = 0.1

    product_ids = {}

    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//table[@id="productlist-table"]/tbody/tr')
        category = hxs.select('//div[@id="divTitle"]/h1/text()').extract()
        if category:
            category = category[0]
        else:
            category = response.meta.get('category')
        if not category:
            self.log("Couldn't extract category from: %s" % response.url)
            tries = response.meta.get('try', 1)
            if tries < 10:
                self.log("Retrying page: %s" % response.url)
                yield Request(response.url, dont_filter=True, meta={'try': tries + 1})

            else:
                self.log("Gave up retrying: %s. Using blanl category" % response.url)
                self.errors.append("Blank category on page: %s" % response.url)
            category = ''

        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            image_url = product.select('td[@class="imgCol"]/a/img/@src').extract()
            if image_url:
                image_url = urljoin(base_url, image_url[0])
            else:
                image_url = ''
            loader.add_value('image_url', image_url)
            loader.add_xpath('dealer', 'td[@class="mercCol"]/a/img/@alt')
            loader.add_xpath('name', 'td[@class="descCol"]/a/b/text()')
            loader.add_value('category', category)
            loader.add_value('sku', '')

            url = product.select('td[@class="descCol"]/a/@href').extract()[0]
            url = url.partition("?")[0]
            identifier = url.partition('goto/')[-1]
            loader.add_value('identifier', identifier)
            loader.add_value('url', urljoin(base_url, url))

            price = "".join(product.select('td[@class="prodListPrezzo"]/text()').extract())
            if not price:
                continue
            loader.add_value('price', price.strip().replace('.', '').replace(',', '.'))

            shipping_cost = product.select('td[@class="prodListPrezzo"]/span[contains(@class, "deliveryCost")]/text()')[0].re(r'([\d,]+)')
            if shipping_cost:
                loader.add_value('shipping_cost', shipping_cost[0].replace(',', '.'))

            item = loader.load_item()
            if item['identifier'] in self.product_ids:
                item['name'] = self.product_ids[item['identifier']]
            else:
                self.product_ids[item['identifier']] = item['name']
            yield item

        pagination = hxs.select('//div[@class="pagination"]/a/@href').extract()
        for page in pagination:
            url = urljoin(base_url, page)
            yield Request(url, meta={'category': category})

        sub_categories = hxs.select('//tr[@class="subCatsMother"]/td/b/a/@href').extract()
        for sub_cat in sub_categories:
            url = urljoin(base_url, sub_cat)
            yield Request(url)

        all_products = hxs.select('//td[@id="col_sxcent"]/div/a[contains(text(), "Tutte le offerte")]/@href').extract()
        if all_products:
            url = urljoin(base_url, all_products[0])
            yield Request(url)

