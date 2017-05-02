import os
import logging
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy import log


class ConradSpider(BaseSpider):
    name = 'conrad.fr'
    allowed_domains = ['www.conrad.fr', 'conrad.fr']
    start_urls = (
        'http://www.conrad.fr/ce/fr/category/SHOP_B2C_TAB_HOME/Alarme-Electricite-Maison-Jardin',
        'http://www.conrad.fr/ce/fr/category/SHOP_B2C_TAB_TOOLS/Bricolage-Outillage-Mesure',
        'http://www.conrad.fr/ce/fr/category/SHOP_AREA_17374/Connecteurs-secteur'
    )

    category_element_ids = (
        'nav4',
        'nav5',
    )

    RETRY_TIMES = 20
    user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'

    def is_correct_category(self, cat_el_id):
        correct_category = False
        for allowed_cat in self.category_element_ids:
            if cat_el_id == allowed_cat:
                correct_category = True
                break
        return correct_category

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories
        for url in  hxs.select('//div[@class="submenulist"]/div/a/@href').extract():
            #hxs.select("//map[@name='m_entree_secteur_maison' or @name='m_entree_secteur_outil']/area/@href").extract():
            url = urljoin_rfc(get_base_url(response), url)
            url = add_or_replace_parameter(url, 'sort', 'Title-asc')
            yield Request(url,
                          callback=self.parse,
                          meta=response.meta,
                          errback=lambda failure, url=url, meta=response.meta: self.retry_download(failure, url, meta))

        # subcategories
        for url in hxs.select('//li[@class="open "]/ul/li/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            url = add_or_replace_parameter(url, 'sort', 'Title-asc')
            yield Request(add_or_replace_parameter(url, 'perPage', '100'),
                          callback=self.parse,
                          meta=response.meta,
                          errback=lambda failure, url=url, meta=response.meta: self.retry_download(failure, url, meta))

        # More categories
        for url in hxs.select('//div[@class="arealist"]//li/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            url = add_or_replace_parameter(url, 'sort', 'Title-asc')
            yield Request(url,
                          callback=self.parse,
                          meta=response.meta,
                          errback=lambda failure, url=url, meta=response.meta: self.retry_download(failure, url, meta))

        # products
        for product in self.parse_product_list(response):
            yield product

        next = hxs.select('//div[@class="page-navigation"]/a[text()="suivant "]/@href').extract()
        if next:
            url = urljoin_rfc(get_base_url(response), next[0])
            yield Request(url,
                          callback=self.parse,
                          meta=response.meta,
                          errback=lambda failure, url=url, meta=response.meta: self.retry_download(failure, url, meta))

    def parse_product_list(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//div[contains(@class, "list-product-item")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            url = product.select(u'.//div[@class="name"]//a/@href').extract()
            price = product.select(u'.//div[@class="price-info"]/span[@class="current-price"]/text()').extract()
            if url and price:
                url = urljoin_rfc(get_base_url(response), url[0])
                price = price[0].replace(".", "").replace(",", ".")
                # stock = product.select('.//span[@class="rating-availability"]//span[@class="avaibility_green"]')
                product_loader.add_value('url', url)
                product_loader.add_xpath('name', u'.//div[@class="name"]//a/text()')
                product_loader.add_value('price', price)
                product_loader.add_xpath('identifier', u'.//div[@class="bestnr"]/strong/text()')
                product_loader.add_xpath('sku', u'.//div[@class="bestnr"]/strong/text()')
                product_loader.add_xpath('image_url', u'.//div[@class="product-image"]//img/@src')
                product_loader.add_xpath('category', u'//table[@id="nav"]//td[contains(@class, "active")]/a/span/text()')
                # if stock:
                #     product_loader.add_value('stock', 1)
                # else:
                product_loader.add_value('stock', 1)
                yield product_loader.load_item()
            else:
                log.msg("ERROR! No URL or PRICE! %s" % response.url)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        if response.request.meta.get('redirect_times', 0) > 0:
            log.msg('ERROR! Redirection detected %s' % response.url) # redirection conflicts with BSM causing duplicate identifiers
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        price = hxs.select(u'//div[@id="productdetail"]//span[@class="price"]/text()').extract()
        if not price:
            log.msg("ERROR! No PRICE! %s" % response.url)
        # stock = hxs.select('.//div[@id="productdetail"]/span[@class="availability" and text()="in_stock"]')
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//div[@id="productdetail"]//h1/a/text()')
        product_loader.add_value('price', price)
        product_loader.add_xpath('identifier', u'//div[@id="productdetail"]//div[@class="number"]/span/strong/text()')
        product_loader.add_xpath('sku', u'//div[@id="productdetail"]//div[@class="number"]/span/strong/text()')
        image_url = hxs.select('//div[@id="ImageContainer"]//img/@src').extract()
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_xpath('category', u'//table[@id="nav"]//td[contains(@class, "active")]/a/span/text()')

        product_loader.add_value('stock', 1)
        yield product_loader.load_item()


    def retry_download(self, failure, url, meta):
        no_try = meta.get('try', 0) + 1
        self.log('Try %d. Retrying to download %s' % (no_try, url))
        if no_try < self.RETRY_TIMES:
            meta['try'] = no_try
            meta['recache'] = True
            time.sleep(60)
            yield Request(url,
                          dont_filter=True,
                          callback=self.parse,
                          meta=meta,
                          errback=lambda failure, url=url, meta=meta: self.retry_download(failure, url, meta)
                          )
