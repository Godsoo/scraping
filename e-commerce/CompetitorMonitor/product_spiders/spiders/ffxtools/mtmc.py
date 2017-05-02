# -*- coding: utf-8 -*-
"""
Customer: FFX Tools
Website: http://mtmc.co.uk
Crawling process: crawl all categories and scrape all products
Options: extract all options
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/3919

IMPORTANT! Subcategories list and products list can be displayed in different ways.
           Spider always check if it collected at least something from page.
           Also, some categories pages has really nothing on them,
           spiders checks if it's such page by checking for header and body of a list.
           Caught several issues thanks to this.


IMPORTANT! The site seems to be a bit malformed, which causes lxml parse it improperly sometimes.
           Issues was noticed only on product details page.
           The error is machine specific (probably because of some underlying libs) -
           was usually failing on server, while working OK on dev machine.
           To fix this Beautiful Soup is used, it seems to parse HTML just fine.


IMPORTANT! "Spare parts" category is ignore as it does not have any products we need, but have 700k other products


IMPORTANT! Clothes and footwear has unusual options: they are in dropdown lists (2 lists for trousers, 1 list for shoes)
           The price seems the same so the spider just collects all options and assignes the same price to them.
           Example: http://www.mtmc.co.uk/Workwear/Trousers-/-Shorts/Dewalt-Pro-Canvas-Work-Trousers__p-12732858-12732866-76292.aspx
"""
from itertools import product
from urlparse import urljoin
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.utils.markup import remove_entities
from scrapy import log

from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from product_spiders.items import ProductLoaderWithNameStrip, Product
from product_spiders.utils import extract_price
from product_spiders.fuzzywuzzy.fuzz import ratio

__author__ = 'juraseg'


def _soup_el_get_attr(soup_el, attr):
    for name, value in soup_el.attrs:
        if name == attr:
            return value

def _is_price_tag(tag):
    if not tag.name == 'td':
        return False
    class_ = _soup_el_get_attr(tag, 'class')
    if 'price' not in class_ or 'inctax' not in class_:
        return False
    return True


def _build_opt_name(main_name, opt_tuple):
    opt_part = [opt['name'] for opt in opt_tuple]
    if opt_part:
        return '%s (%s)' % (main_name, ' '.join(opt_part))
    else:
        return main_name


def _build_opt_id(main_id, opt_tuple):
    parts = [main_id] + [opt['id'] for opt in opt_tuple]
    return ':'.join(parts)


def _retry_page(response, max_tries=10):
    tries = response.meta.get('try', 0)
    if tries < max_tries:
        return Request(response.url, callback=response.request.callback, dont_filter=True, meta={'try': tries + 1})
    else:
        return None


def _main_name_in_opt_name(main_name, opt_name):
    if ratio(main_name.lower(), opt_name.lower()) > 60:
        return True


class MTMCSpider(BaseSpider):
    name = 'mtmc_ffx'
    allowed_domains = ('mtmc.co.uk', )

    start_urls = ('http://www.mtmc.co.uk/', )

    errors = []

    def log(self, message, level=log.DEBUG):
        msg = "[%s] %s" % (self.__class__.__name__, message)
        super(MTMCSpider, self).log(msg)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories links
        cats = hxs.select("//div[@id='UC_CategoryMenuAccordion_menCategory']//a[@class='KartrisMenu-Link']")
        for cat in cats:
            cat_name = cat.select("text()").extract()[0].strip()
            url = cat.select("@href").extract()[0]
            # ignore "Spare parts" category
            if 'spare parts' in cat_name.lower() or 'spare-parts' in url.lower():
                self.log("Skipping category: %s" % cat_name)
                continue
            url = urljoin(get_base_url(response), url)

            yield Request(url, callback=self.parse_subcat)

    def parse_subcat(self, response):
        hxs = HtmlXPathSelector(response)

        # subcategories (if any)
        subcats = hxs.select("//div[contains(@class, 'subcategories')]//div[@class='item']//h2/a/@href").extract()
        for subcat in subcats:
            url = urljoin(get_base_url(response), subcat)
            yield Request(url, callback=self.parse_subcat)

        subcats2 = hxs.select("//div[contains(@class, 'subcategories_link')]/a/@href").extract()
        for subcat in subcats2:
            url = urljoin(get_base_url(response), subcat)
            yield Request(url, callback=self.parse_subcat)

        # pagination
        pagination = hxs.select("//div[@class='itempager']/a/@href").extract()
        for page in pagination:
            url = urljoin(get_base_url(response), page)
            yield Request(url, callback=self.parse_subcat)

        # products (if any)
        prods = hxs.select("//div[contains(@class, 'products')]//div[@class='item']//h2/a/@href").extract()
        for prod in prods:
            url = urljoin(get_base_url(response), prod)
            yield Request(url, callback=self.parse_product)

        if not subcats and not subcats2 and not prods:
            # check if there is any data
            header = hxs.select("//div[@id='cntMain_tabContainer']/div[@id='cntMain_tabContainer_header']/*").extract()
            body = hxs.select("//div[@id='cntMain_tabContainer']/div[@id='cntMain_tabContainer_body']/*").extract()
            if header or body:
                self.errors.append("Nothing found on page: %s" % response.url)

    def parse_product(self, response):
        soup = BeautifulSoup(response.body)
        if not soup.find('div', attrs={'class': 'product'}):
            retry_request = _retry_page(response)
            if retry_request:
                yield retry_request
            else:
                self.log("Error parsing page, couldn't extract product name: %s" % response.url)
            return
        main_name = soup.find('div', attrs={'class': 'product'}).h1.text
        main_name = remove_entities(main_name)
        brand_el = soup.find(lambda tag: tag.name == 'td' and 'brand' in tag.text.lower())
        brand = brand_el.findNextSibling('td').text.strip() if brand_el else ''
        cat_names = [span.a.text
                     for span in soup.find('div', attrs={'class': 'breadcrumbtrail'}).span.findAll('span')
                     if span.a][2:]
        image_url = soup.find('img', {'itemprop': 'image'})
        image_url = image_url['src'] if image_url else None

        table = soup.find('table', id='responsive-table')
        options = soup.findAll('div', attrs={'class': 'option'})
        if table:
            for row in table.findAll('tr'):
                # Skip head row
                if not row.td:
                    continue

                name = row.find('span', attrs={'class': 'name'}).text
                name = remove_entities(name)
                if not _main_name_in_opt_name(main_name, name):
                    name = main_name + ' ' + name
                identifier = row.find('span', attrs={'class': 'codenumber'})
                if not identifier:
                    self.errors.append("Identifier not found for products on page: %s" % response.url)
                    continue
                identifier = identifier.text

                price = row.find(_is_price_tag).text
                real_price = extract_price(price)
                if real_price < 15:
                    shipping_cost = 3
                elif real_price < 40:
                    shipping_cost = 4
                elif real_price < 130:
                    shipping_cost = 7
                else:
                    shipping_cost = None

                loader = ProductLoaderWithNameStrip(Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('url', response.url)
                loader.add_value('brand', brand)
                loader.add_value('identifier', identifier)
                loader.add_value('sku', identifier)
                loader.add_value('price', price)
                for cat_name in cat_names:
                    loader.add_value('category', cat_name)
                loader.add_value('shipping_cost', shipping_cost)
                loader.add_value('image_url', image_url)

                yield loader.load_item()
        elif options:
            main_id = response.url.split('.')[-2].split('p-')[-1]
            price = soup.find('span', attrs={'class': 'inctax'}).span.text
            real_price = extract_price(price)
            if real_price < 15:
                shipping_cost = 3
            elif real_price < 40:
                shipping_cost = 4
            elif real_price < 130:
                shipping_cost = 7
            else:
                shipping_cost = None

            results = {}
            for opt in options:
                opt_name = opt.label.span.text
                results[opt_name] = []
                for subopt in opt.select.findAll('option'):
                    subopt_name = subopt.text
                    subopt_value = _soup_el_get_attr(subopt, 'value')
                    if subopt_value == '0':
                        continue
                    results[opt_name].append({
                        'id': remove_entities(subopt_name).replace('"', ''),
                        'name': opt_name + ': ' + subopt_name
                    })
            for opt_tuple in product(*results.values()):
                name = _build_opt_name(main_name, opt_tuple)
                identifier = _build_opt_id(main_id, opt_tuple)
                loader = ProductLoaderWithNameStrip(Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('url', response.url)
                loader.add_value('brand', brand)
                loader.add_value('identifier', identifier)
                loader.add_value('sku', identifier)
                loader.add_value('price', price)
                for cat_name in cat_names:
                    loader.add_value('category', cat_name)
                loader.add_value('shipping_cost', shipping_cost)
                loader.add_value('image_url', image_url)

                yield loader.load_item()