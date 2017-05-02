# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4530
"""
from decimal import Decimal

from scrapy import Spider, Request

from product_spiders.items import ProductLoaderWithNameStrip as ProductLoader, Product
from product_spiders.spiders.BeautifulSoup import BeautifulSoup


class VisionDirectSpider(Spider):
    name = 'specsavers_ie-visiondirect.ie'
    allowed_domains = ('visiondirect.ie', )
    cats = [('http://www.visiondirect.ie/contact-lenses', 'Contact Lenses'),
            ('http://www.visiondirect.ie/solutions-eye-care', 'Contact Lens Solutions'),
            ('http://www.visiondirect.ie/eye-care', 'Eye Care')]

    def start_requests(self):
        for c in self.cats:
            yield Request(c[0], meta={'category': c[1]})

    def parse(self, response):
        # using beautiful soup since the html is broken and cannot be parsed with lxml
        soup = BeautifulSoup(response.body)
        urls = soup.findAll('a', {'class': 'products-list__item'})
        for url in urls:
            yield Request(url['href'], callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        soup = BeautifulSoup(response.body)
        try:
            price = soup.find('span', {'class': 'price ours'}).text
        except AttributeError:
            self.log('price not found {}'.format(response.url))
            return

        image_url = soup.find('img', itemprop='image')['src']
        identifier = soup.find('form', id='product_addtocart_form')
        identifier = identifier['action'].split('product/')[-1].split('/')[0]
        loader.add_value('image_url', image_url)
        loader.add_value('price', price)
        name = soup.find('h1', itemprop='name').text.strip()
        loader.add_value('name', name)
        loader.add_value('category', response.meta.get('category', ''))
        brand = soup.find('span', itemprop='manufacturer').text.replace('&nbsp;', '').split('by', 1)[1].strip()
        loader.add_value('brand', brand)
        loader.add_value('url', response.url)
        sku = soup.find('input', id='eye')
        loader.add_value('identifier', identifier)
        if sku:
            loader.add_value('sku', sku['value'])
        shipping_cost = '5.98'
        if loader.get_output_value('price') <= Decimal(59):
            shipping_cost = '9.98'
        loader.add_value('shipping_cost', shipping_cost)
        yield loader.load_item()


