# -*- coding: utf-8 -*-
"""
Customer: FFX Tools
Website: http://uktoolcentre.co.uk
Crawling process: crawl all categories and scrape all products
Options: extract all options
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/3921

IMPORTANT! Sometimes when you go to subcategory the website lists even more subcategories.
           Example: http://www.uktoolcentre.co.uk/Hand-Tools/Torches/


IMPORTANT! Some options on product pages has the same product code. Only different is either:
           1) Voltage (240V or 110V)
           2) Number of items in pack (1, 5, 10)
           This is handled by spider by extracting information about voltage and number of items from product name
           and adding this information to identifier.


IMPORTANT! The site seems to be a bit malformed, which causes lxml parse it improperly sometimes.
           Issues was noticed only on product details page.
           The error is machine specific (probably because of some underlying libs) -
           was usually failing on server, while working OK on dev machine.
           To fix this Beautiful Soup is used, it seems to parse HTML just fine.


"""
import re
from urlparse import urljoin
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from product_spiders.spiders.BeautifulSoup import BeautifulSoup

from product_spiders.items import ProductLoaderWithNameStrip, Product

__author__ = 'juraseg'


volt_regex = re.compile(r"\b(\d+v)\b", re.I)


def get_volts_from_name(name):
    """
    >>> get_volts_from_name("Bosch GBH8-45DV SDS Max 8kg Rotary Combi Hammer Drill 240v")
    '240v'
    >>> get_volts_from_name("Bosch GBH8-45DV SDS Max 8kg Rotary Combi Hammer Drill 110v")
    '110v'
    >>> get_volts_from_name("Bosch GBH8-45DV SDS Max 8kg Rotary Combi Hammer Drill")
    """
    m = volt_regex.search(name)
    if m:
        return m.group(1)
    else:
        return None


pack_regexes = [
    re.compile(r"\((\d+) pack\)", re.I),
    re.compile(r"\(pack of (\d+)\)", re.I),
]


def get_pack_of_from_name(name):
    """
    >>> get_pack_of_from_name("Metal drill bits HSS-G Standardline, DIN 338 13mm (5 Pack)")
    '5'
    >>> get_pack_of_from_name("Metal drill bits HSS-G Standardline, DIN 338 13mm (Pack of 5)")
    '5'
    >>> get_pack_of_from_name("Metal drill bits HSS-G Standardline, DIN 338 13mm (1)")
    """
    for reg in pack_regexes:
        m = reg.search(name)
        if m:
            return m.group(1)

    return None


class UkToolCentreSpider(BaseSpider):
    name = 'uktoolcentre_ffx'
    allowed_domains = ('uktoolcentre.co.uk', )

    start_urls = ('http://www.uktoolcentre.co.uk/', )

    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select("//ul[@id='mainNav']//a/@href").extract():
            url = urljoin(get_base_url(response), url)
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        # subcategories, like on page: http://www.uktoolcentre.co.uk/Hand-Tools/Torches/
        for url in hxs.select("//div[@class='cat-box']//a[@class='view-products']/@href").extract():
            url = urljoin(get_base_url(response), url)
            yield Request(url, callback=self.parse_category)

        for prod_el in hxs.select("//div[contains(@class, 'prod-box grid')]"):
            for url in prod_el.select(".//a/@href").extract():
                url = urljoin(get_base_url(response), url)
                yield Request(url, callback=self.parse_product)

        for url in hxs.select("//ul[@class='pagination']/li/a/@href").extract():
            url = urljoin(get_base_url(response), url)
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        try:
            # fall back to Beautiful Soup
            soup = BeautifulSoup(response.body)
            hxs = HtmlXPathSelector(response)

            container = soup.find('div', attrs={'class': 'nosto_product'})

            brand = container.find('span', attrs={'class': 'brand'}).text
            cat_names = [el.text for el in soup.find("div", id='bct').findAll('a')][1:]
            main_id = container.find('span', attrs={'class': 'product_id'}).text
            availability = container.find('span', attrs={'class': 'availability'}).text
            image_url = soup.find('img', id='main-image').attrMap['src']

            options = soup.find('table', id='sku-table')
            if not options:
                name = soup.find('div', id='product-page-info').find('h1').text
                price = container.find('span', attrs={'class': 'price'}).text

                loader = ProductLoaderWithNameStrip(Product(), selector=hxs)
                loader.add_value('brand', brand)
                for cat_name in cat_names:
                    loader.add_value('category', cat_name)
                loader.add_value('name', name)
                loader.add_value('identifier', main_id)
                loader.add_value('price', price)
                loader.add_value('url', response.url)
                loader.add_value('sku', main_id)
                loader.add_value('image_url', image_url)

                if availability.lower() == 'outofstock':
                    loader.add_value('stock', 0)

                yield loader.load_item()
            else:
                option_ids = []
                for opt in options.findAll('tr'):
                    sec_id = opt.findAll('td')[1].find('small').text
                    name = opt.findAll('td')[1].text.replace(sec_id, '')
                    sec_id = sec_id.strip('(').strip(')')
                    identifier = main_id + ':' + sec_id
                    volts = get_volts_from_name(name)
                    if volts is not None:
                        identifier = identifier + ':' + volts
                    pack_of = get_pack_of_from_name(name)
                    if pack_of is not None:
                        identifier = identifier + ':' + pack_of

                    if identifier in option_ids:
                        option_id = opt.find('input', attrs={'name': 'ID'}).get('value')
                        identifier = identifier + ':' + option_id

                    option_ids.append(identifier)

                    price = opt.find('td', attrs={'class': 'price'}).text.strip(u'\xa3').strip('&pound;')

                    loader = ProductLoaderWithNameStrip(Product(), response=response)
                    loader.add_value('brand', brand)
                    for cat_name in cat_names:
                        loader.add_value('category', cat_name)
                    loader.add_value('name', name)
                    loader.add_value('identifier', identifier)
                    loader.add_value('price', price)
                    loader.add_value('url', response.url)
                    loader.add_value('sku', main_id)
                    loader.add_value('image_url', image_url)

                    if availability.lower() == 'outofstock':
                        loader.add_value('stock', 0)
                    
                    yield loader.load_item()

        except IndexError as e:
            # try loading page again
            tries = response.meta.get('try', 0)
            if tries < 10:
                yield Request(response.url, callback=self.parse_product, dont_filter=True, meta={'try': tries + 1})
            else:
                self.errors.append("Error scraping page %s: %s" % (response.url, str(e)))
                raise
