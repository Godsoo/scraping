# -*- coding: utf-8 -*-
import re
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.spiders.orange_new import (
    make_product_from_response,
    filter_color,
    filter_duplicates_with_higher_price,
    InvalidCategory,
)

# account specific fields
channel = 'Digitec'

device_identifier_regex = re.compile(".*Artikel=(\d+)")

def extract_device_identifier(url):
    """
    >>> extract_device_identifier('https://www.digitec.ch/ProdukteDetails2.aspx?Reiter=Details&Artikel=286208')
    '286208'
    """
    m = device_identifier_regex.search(url)
    identifier = m.group(1)
    return identifier

device_name_regex0 = re.compile('(.*) \([^,]*, ([^,]*GB), ?([^,]*), ?([^,]*)\)', re.I)
device_name_regex = re.compile('(.*) \(([^,]*GB), ?([^,]*), ?([^,]*)[\.]{3}', re.I)
device_name_regex2 = re.compile('(.*) \(([^,]*GB), ?([^,]*), ?([^,]*)\)', re.I)
device_name_regex3 = re.compile('(.*) \((\d*GB), ?([^,]*)\)', re.I)
device_name_regex31 = re.compile('(.*) \([^,]*, (\d*GB), ?([^,]*)\)', re.I)
device_name_regex4 = re.compile('(.*) \(([^,]*), ?([^,]*)\)', re.I)
device_name_regex5 = re.compile('(.*) \(([^,]*)\)', re.I)


def filter_device_name(name, brand=None):
    """
    >>> filter_device_name('Sony Xperia Z2 - 16 GB - Violett (16GB, Purple)')
    'Sony Xperia Z2 - 16 GB'
    >>> filter_device_name('Samsung S3800 Rex 70 (0.01GB,)')
    'Samsung S3800 Rex 70'
    >>> filter_device_name('Emporia CLICK (Schwarz)')
    'Emporia CLICK'
    >>> filter_device_name('Nokia 301 (0.26GB, Dual SIM, Schwarz)')
    'Nokia 301 Dual SIM'
    >>> filter_device_name('HTC Desire 310 (4GB, Blau)')
    'HTC Desire 310 4GB'
    >>> filter_device_name('Archos Platinum 45 (4GB, Dual SIM, Schwarz)', 'Archos')
    'Archos Platinum 45 4GB Dual SIM'
    >>> filter_device_name('Samsung G7102 Galaxy Grand 2 DUOS (8GB, Dual SIM, Schwarz...')
    'Samsung G7102 Galaxy Grand 2 DUOS 8GB Dual SIM'
    >>> filter_device_name('Samsung Galaxy S5 (16GB, Charcoal Black)')
    'Samsung Galaxy S5 16GB'
    >>> filter_device_name('Moto G (2nd Gen) (8GB, Dual Sim, Schwarz)')
    'Moto G (2nd Gen) 8GB Dual Sim'
    >>> filter_device_name('Blackphone (16GB, Schwarz)', 'Blackphone')
    'Blackphone 16GB'
    >>> filter_device_name('Galaxy J1 (4.30", 4GB, Dual SIM, Weiss)')
    'Galaxy J1 4GB Dual SIM'
    >>> filter_device_name('Galaxy Note Edge (5.60", 32GB, Schwarz)')
    'Galaxy Note Edge 32GB'
    """
    res = name
    # if brand:
    #     res = remove_brand(name, brand)

    m0 = device_name_regex0.search(res)
    m = device_name_regex.search(res)
    m2 = device_name_regex2.search(res)
    m3 = device_name_regex3.search(res)
    m31 = device_name_regex31.search(res)
    m4 = device_name_regex4.search(res)
    m5 = device_name_regex5.search(res)

    if m0:
        name, memory, dualsim, color = m0.groups()
        if color in name:
            name = name.replace(color, '')
        name = name.strip()

        if not memory.startswith('0') and 'gb' not in name.lower():
            name = name + ' ' + memory
        if not 'dual' in name.lower():
            name = name + ' ' + dualsim
        res = name
    elif m:
        name, memory, dualsim, color = m.groups()
        if color in name:
            name = name.replace(color, '')
        name = name.strip()

        if not memory.startswith('0') and 'gb' not in name.lower():
            name = name + ' ' + memory
        if not 'dual' in name.lower():
            name = name + ' ' + dualsim
        res = name
    elif m2:
        name, memory, dualsim, color = m2.groups()
        if color in name:
            name = name.replace(color, '')
        name = name.strip()

        if not memory.startswith('0') and 'gb' not in name.lower():
            name = name + ' ' + memory
        if not 'dual' in name.lower():
            name = name + ' ' + dualsim
        res = name
    elif m3:
        name, memory, color = m3.groups()
        if color in name:
            name = name.replace(color, '')
        name = name.strip()

        if not memory.startswith('0') and 'gb' not in name.lower():
            name = name + ' ' + memory
        res = name
    elif m31:
        name, memory, color = m31.groups()
        if color in name:
            name = name.replace(color, '')
        name = name.strip()

        if not memory.startswith('0') and 'gb' not in name.lower():
            name = name + ' ' + memory
        res = name
    elif m4:
        name, part1, color = m4.groups()
        if color in name:
            name = name.replace(color, '')
        name = name.strip()

        res = name
    elif m5:
        name, color = m5.groups()
        if color in name:
            name = name.replace(color, '')
        name = name.strip()

        res = name

    # do not filter colour for Archos devices
    if brand is None or 'Archos'.lower() not in brand.lower():
        res = filter_color(res)
    return res


def _make_product(response, operator, plan_name, per_month, period, one_time_charge, strip_operator=False):
    return make_product_from_response(
        response, operator, channel, plan_name, per_month, period, one_time_charge,
        strip_operator=strip_operator,
        ignore_rec_charge_diff=True)


def pick_product_brand(name):
    """
    >>> pick_product_brand('Oneplus One (64GB, Schwarz)')
    ('Oneplus', 'One (64GB, Schwarz)')
    >>> pick_product_brand('Blackphone (16GB, Schwarz)')
    ('Blackphone', 'Blackphone (16GB, Schwarz)')
    >>> pick_product_brand('Ruggear Rg100 Dual Sim')
    ('Ruggear', 'Rg100 Dual Sim')
    """
    brands = [
        'Oneplus',
        'Blackphone',
        'Ruggear'
    ]
    brand_remove = {
        'Oneplus',
        'Ruggear'
    }
    for brand in brands:
        regex = '%s' % brand
        m = re.search(regex, name, re.I)
        if m:
            if brand in brand_remove:
                found = m.group(0)
                new_name = name.replace(found, '').strip()
                return brand, new_name
            else:
                return brand, name
    return '', name


price_plan_type_values = {
    'normal': '2',
    'young': '4'
}

private_price_plan = ('normal', '2')
young_price_plan = ('young', '4')


class DigitecSpider(BaseSpider):
    name = 'orange_digitec.ch'
    allowed_domains = ['digitec.ch']
    start_urls = (
        # cell phones
        'https://www.digitec.ch/de/s1/producttype/mobile-phone-24?tagIds=82',
    )

    all_products = 0
    out_of_stock_products = 0

    private_processed_devices = set()
    young_processed_devices = set()

    private_finished = False

    def __init__(self, *a, **kw):
        super(DigitecSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.loaded_names = set()
        self.products = []

    def spider_idle(self, spider):
        """
        Runs after all pages and items processed but before closing
        Populates all 'out of stock' items as they were just stored in attribute
        """
        self.log("Spider idle")

        if not self.private_finished:
            self.private_finished = True
            request = Request(self.start_urls[0], dont_filter=True, callback=self.parse)
            self._crawler.engine.crawl(request, self)
        else:
            if self.products:
                request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse)
                self._crawler.engine.crawl(request, self)

    def closing_parse(self, response):
        self.log("Processing items")
        self.products = filter_duplicates_with_higher_price(self.products)
        while self.products:
            yield(self.products.pop())

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select("//article[contains(@class, 'product')]")

        for i, p in enumerate(products):
            brand = p.select(".//div[@class='product-name']/span/text()").extract()
            brand = brand[0] if brand else ''
            name = p.select(".//div[@class='product-name']/text()").extract()[-1]

            if not brand:
                brand, name = pick_product_brand(name)

            name = filter_device_name(name, brand)

            stock_el = p.select(".//div[contains(@class, 'availability')]")
            if stock_el.select(".//*[@class='questionmark']"):
                stock = 0
            else:
                stock = None

            if stock == 0:
                continue

            if not name in self.loaded_names:
                url = p.select("a/@href").extract()[0]
                url = urljoin(get_base_url(response), url)

                yield Request(
                    url,
                    callback=self.parse_product,
                    meta={
                        'product': {
                            'device_name': name,
                            'brand': brand,
                            'url': url,
                            'in_stock': None
                        }
                    },
                    dont_filter=True
                )

        next_page = hxs.select("//div[contains(@class, 'loadMore')]//a/@href").extract()
        if next_page:
            url = urljoin(get_base_url(response), next_page[0])
            yield Request(
                url,
                callback=self.parse
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        image_url = hxs.select("//meta[@itemprop='image']/@content").extract()
        if image_url:
            image_url = urljoin(get_base_url(response), image_url[0])
        else:
            image_url = ''

        product = {
            'device_name': response.meta['product']['device_name'],
            'url': response.meta['product']['url'],
            'brand': response.meta['product']['brand'],
            'in_stock': response.meta['product']['in_stock'],
            'image_url': image_url,
        }

        subscription_url = hxs.select("//div[@class='product-subscription']/a/@href").extract()
        if not subscription_url:
            return
        subscription_url = urljoin(get_base_url(response), subscription_url[0])

        yield Request(
            subscription_url,
            callback=self.parse_subscription,
            meta={
                'product': product
            },
            dont_filter=True
        )

    def parse_subscription(self, response):
        hxs = HtmlXPathSelector(response)

        subscription_url2 = hxs.select("//a[contains(text(), 'With a new contract')]/@href").extract()
        if not subscription_url2:
            subscription_url2 = hxs.select("//a[contains(text(), 'Mit einem neuen Vertrag')]/@href").extract()

        subscription_url2 = urljoin(get_base_url(response), subscription_url2[0])

        yield Request(
            subscription_url2,
            callback=self.parse_subscription2,
            meta=response.meta,
            dont_filter=True
        )

    def parse_subscription2(self, response):
        hxs = HtmlXPathSelector(response)

        form_el = hxs.select("//form[@id='mainForm']")

        formdata = {
            '_nonce_': form_el.select(".//*[@name='_nonce_']/@value").extract()[0],
            'persist.AudienceBlockEditViewModel.SubscriptionAudienceId': "",
            'cs': form_el.select(".//*[@name='cs']/@value").extract()[0],
        }

        device_name = response.meta['product']['device_name']

        if device_name not in self.private_processed_devices:
            pp_type, value = private_price_plan
        else:
            pp_type, value = young_price_plan
        data = formdata.copy()
        data['AudienceBlockEditViewModel.ook-SubscriptionAudienceId-' + value] = ''

        meta = response.meta.copy()
        meta['price_plan_type'] = pp_type
        meta['price_plan_value'] = value

        yield FormRequest(
            response.url,
            callback=self.parse_subscription22,
            formdata=data,
            meta=meta,
            dont_filter=True
        )

    def parse_subscription22(self, response):
        hxs = HtmlXPathSelector(response)

        form_el = hxs.select("//form[@id='mainForm']")

        price_plan_type = response.meta['price_plan_type']
        price_plan_value = response.meta['price_plan_value']
        device_name = response.meta['product']['device_name']
        if price_plan_type == 'normal':
            self.private_processed_devices.add(device_name)
        elif price_plan_type == 'young':
            self.young_processed_devices.add(device_name)

        formdata = {
            '_nonce_': form_el.select(".//*[@name='_nonce_']/@value").extract()[0],
            'AudienceBlockController.save': "",
            'cs': form_el.select(".//*[@name='cs']/@value").extract()[0],
        }

        data = formdata.copy()
        data['persist.AudienceBlockEditViewModel.SubscriptionAudienceId'] = price_plan_value

        yield FormRequest(
            response.url,
            callback=self.parse_subscription3,
            formdata=data,
            meta=response.meta,
            dont_filter=True
        )

    def parse_subscription3(self, response):
        hxs = HtmlXPathSelector(response)

        form_el = hxs.select("//form[@id='mainForm']")

        formdata = {}

        for el in form_el.select(".//input"):
            name = el.select("@name").extract()[0]
            value = el.select("@value").extract()[0] if el.select("@value").extract() else ''
            formdata[name] = value

        formdata['AllSubscriptionDataSetsVisible4'] = ''

        yield FormRequest(
            response.url,
            callback=self.parse_price_plans,
            formdata=formdata,
            meta=response.meta,
            dont_filter=True
        )

    def parse_price_plans(self, response):
        hxs = HtmlXPathSelector(response)

        self.log("[[DIGITEC]] Parsing price plans for device: %s (%s)" %
                 (response.meta['product']['device_name'], response.meta['product']['url']))

        container = hxs.select("//div[@id='SubscriptionBlockControllerBlock']/div[@class='col-xs-12'][2]")

        for i in xrange(1, 4):
            operator = container.select("h2[%d]//text()" % i).extract()

            if not operator:
                self.log("[[DIGITEC]] Operator %d not found" % i)
                continue

            operator = operator[0]
            operator = operator.strip('.')

            # skip sunrise
            if operator.lower() == 'sunrise':
                continue

            if operator.lower() == 'salt':
                operator = 'Orange'

            rows = container.select("//table[@class='bill'][%i]//tr[@class='line-bottom']" % i)

            for row in rows:
                plan_name = row.select(".//td[1]/a/text()").extract()[0].strip()
                per_month = row.select(".//td[2]/text()").re('([\d\.]+)')[0]
                try:
                    period = '12 Months'
                    one_time_charge = row.select(".//td[3]/button/text()").re('([\d\.]+)')[0]
                    product = _make_product(response, operator, plan_name, per_month, period, one_time_charge,
                                            strip_operator=True)

                    self.products.append(product)

                    period = '24 Months'
                    one_time_charge = row.select(".//td[4]/button/text()").re('([\d\.]+)')[0]
                    product = _make_product(response, operator, plan_name, per_month, period, one_time_charge,
                                            strip_operator=True)
                    self.log("[[DIGITEC]] Adding product: %s" % product['identifier'])
                    self.products.append(product)
                except InvalidCategory:
                    self.log("Invalid category for price plan: %s" % plan_name)
