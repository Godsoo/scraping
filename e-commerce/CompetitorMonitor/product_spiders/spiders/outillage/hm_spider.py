import os
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import remove_punctuation_and_spaces


class HmdiffussionSpider(BaseSpider):
    name = "hmdiffusion.com"
    allowed_domains = ["hmdiffusion.com"]
    start_urls = ["http://www.hmdiffusion.com/"]

    def parse(self, response):
        """ Obtains all the categories of the main page.
        """
        hxs = HtmlXPathSelector(response)
        sites = hxs.select('//a[@class="_h snormale"]/@href')
        for site in sites:
            relative_url = site.extract()
            url = self._urljoin(response, relative_url)
            yield Request(url, callback=self.parse_page)

    # Used by Big Site Method Spider
    def parse_product(self, response):
        for item in self.parse_page(response):
            yield item

    def parse_page(self, response):
        """ Parse the items of the page, in case of pagination makes a request
            for each page
        """
        hxs = HtmlXPathSelector(response)
        one_product = hxs.select('//div[@id="ficheProduitPied"]')
        if one_product:
            yield self._single_product(one_product, response)
        else:
            products = hxs.select('//div[@class="colonne_1"]')
            pages = hxs.select('//div[@id="selection_page_haut"]/'
                               'form/label/select/option/@value').extract()
            if  not pages:
                for product in products:
                    if product.select('div/div/span[@class="autreinfo"]'):
                       relative_url = product.select('div[@class="ligne_titre"]/a/@href').extract()[0]
                       url = urljoin_rfc('http://www.hmdiffusion.com/', relative_url, response.encoding)
                       yield Request(url, callback=self.parse_page)
                    else:
                        yield self._item_product(product, response)
            else:
                for page in pages:
                    url = urljoin_rfc(get_base_url(response),
                                       page,
                                       response.encoding)
                    yield Request(url, callback=self.parse_pagination)

    def parse_pagination(self, response):
        """ Parse the diferent pages in case of pagination.
        """
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="colonne_1"]')
        for product in products:
            if product.select('div/div/span[@class="autreinfo"]').extract():
                xpath = 'div[@class="ligne_titre"]/a/@href'
                url = ("http://www.hmdiffusion.com/" + product.select(xpath).extract()[0].strip())
                yield Request(url, callback=self.parse_page)
            else:
                yield self._item_product(product, response)

    def _single_product(self, product, response):
        """ Some pages have only one product, and got a different structure.
            This function returns the unique Item on this type of pages.
        """
        hxs = HtmlXPathSelector(response)
        try:
            category = hxs.select('//div[@id="chemin_os"]//a/span[@itemprop="title"]/text()').extract()[-2].strip()
        except:
            category = None
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=product)
        loader.add_value('url', response.url)
        name = product.select('div[@id="fichetitre"]/text()')
        name = name[0].extract().strip()
        name = name.replace('- OFFRE SPECIALE !', '').strip()
        loader.add_value('name', name)
        loader.add_xpath('sku', './/span[@class="reference"]/text()', re=r'R\xe9f. (.*)')
        identifier = remove_punctuation_and_spaces(name).lower()
        loader.add_value('identifier', identifier)
        image = product.select('.//div[@id="lien_zoom0"]//img/@src').extract()
        if image:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image[0]))
        if category:
            loader.add_value('category', category)
        xpath = 'form/div//div/div/div/div/b[@class="prix"]/text()'
        if product.select(xpath):
            price = product.select(xpath).extract()[0]
            loader.add_value('price', self._encode_price(price))
        # stock = hxs.select('//span[@content="in_stock"]')
        # if stock:
        #     loader.add_value('stock', 1)
        # else:
        loader.add_value('stock', 1)
        return loader.load_item()

    def _item_product(self, product, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=product)
        xpath = 'div[@class="ligne_titre"]/a/@href'
        url = ''
        try:
            category = hxs.select('//div[@id="chemin_os"]//a/span[@itemprop="title"]/text()').extract()[-1].strip()
        except:
            category = None
        if product.select(xpath).extract():
            url = ("http://www.hmdiffusion.com/" + product.select(xpath).extract()[0].strip())
        loader.add_value('url', url)
        name = product.select('div[@class="ligne_titre"]/a/span/strong/text()')
        name = name[0].extract().strip()
        name = name.replace('- OFFRE SPECIALE !', '').strip()
        loader.add_value('name', name)
        xpath = 'div[@class="lignebeige"]/div[@class="bloc_prix bloc_prix deuxprix"]/b[@class="prix"]/text()'
        if product.select(xpath):
            price = product.select(xpath).extract()[0]
            loader.add_value('price', self._encode_price(price))
        else:
            xpath = 'div[@class="lignebeige"]/div[@class="bloc_prix "]/b[@class="prix"]/text()'
            if product.select(xpath):
                price = product.select(xpath).extract()[0]
                loader.add_value('price', self._encode_price(price))
            else:
                xpath = 'div[@class="lignebeige"]/div[@class="bloc_prix deuxprix"]/b[@class="prix"]/text()'
                if product.select(xpath):
                    price = product.select(xpath).extract()[0]
                    loader.add_value('price', self._encode_price(price))
        sku = product.select('.//div[@class="lignebeige"]//span[@class="reference"]/text()')[1].extract().strip()
        if category:
            loader.add_value('category', category)
        identifier = remove_punctuation_and_spaces(name).lower()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        image = product.select('.//preceding-sibling::div[@class="colonne_0"]//img/@src').extract()
        if image:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image[0]))

        loader.add_value('stock', 1)
        return loader.load_item()

    def _urljoin(self, response, url):
        """Helper to convert relative urls to absolute"""
        return urljoin_rfc(response.url, url, response.encoding)

    def _encode_price(self, price):
        return price.replace(',', '.').encode("ascii", "ignore")
