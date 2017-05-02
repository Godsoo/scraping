# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy import log
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from . import make_product_from_response, InvalidCategory, filter_duplicates_with_higher_price

# account specific fields
operator = 'Sunrise'
channel = 'Direct'

class SunriseSpider(BaseSpider):
    name = 'orange_sunrise.ch'
    allowed_domains = ['sunrise.ch']
    start_urls = (
        'http://www1.sunrise.ch/Handys-cbSyXAqFI.h8IAAAE6.r0ivvoJ-Sunrise-Residential-Site-WFS-de_CH-CHF.html',
    )

    products = []

    def __init__(self, *a, **kw):
        super(SunriseSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        """
        Runs after all pages and items processed but before closing
        Populates all 'out of stock' items as they were just stored in attribute
        """
        self.log("Spider idle")

        if self.products:
            request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse)
            self._crawler.engine.crawl(request, self)

    def closing_parse(self, response):
        self.log("Processing items")
        self.products = filter_duplicates_with_higher_price(self.products)
        while self.products:
            yield(self.products.pop())

    def parse(self, response):
        data = {
            'CatalogDomainUUID': 'zp3AqFI.SSYAAAEkQ_ZQzDCe',
            'CatalogName': '01_Privatkunden',
            'EnableProductComparison': '',
            'FilterDiv': 'ProductFilterContainer',
            'FilterPipeline': 'ViewHardwareShopProducts-FilterRowView',
            'FilterRootCategoryName': 'HardwareFilter',
            'QueryParameters': 'CatalogCategoryID%3DSyXAqFI.h8IAAAE6.r0ivvoJ%26undefined',
            'TargetDiv': 'RowContainer'
        }

        url = 'http://www1.sunrise.ch/is-bin/INTERSHOP.enfinity/WFS/Sunrise-Residential-Site/en_CH/-/CHF/ViewHardwareShop-IncludeHardwareFilter'

        yield FormRequest(url, formdata=data, callback=self.parse_initial_post_req)

    def parse_initial_post_req(self, response):
        yield Request('http://www1.sunrise.ch/is-bin/INTERSHOP.enfinity/WFS/Sunrise-Residential-Site/de_CH/-/CHF/ViewHardwareShopProducts-FilterRowView',
                      callback=self.parse_list)

    def parse_list(self, response):
        self.log("Parse")
        hxs = HtmlXPathSelector(response)
        for product in hxs.select('//div[@class="preview_box"]'):
            image_url = product.select('.//div[@class="bild"]//img/@src').extract()[0]
            url = product.select('.//form/@action').extract()[0]
            product_uuid = product.select('.//input[@name="ProductUUID"]/@value').extract()[0]
            url += '?ProductUUID=%s' % product_uuid
            self.log("Yielding product: %s" % url)
            req = Request(url, callback=self.parse_product_page, meta={'image_url': image_url, 'uuid': product_uuid})
            yield req

        for url in hxs.select('//div[@id="PagingBar"]//li[not(@class) or @class!="pageSize"]/a/input/@value').extract():
            self.log("Yielding page: %s" % url)
            req = Request(url, callback=self.parse_list)
            yield req

    def parse_product_page(self, response):
        self.log("Parse product page")
        hxs = HtmlXPathSelector(response)

        specification_url = hxs.select("//div[@class='furtherInformationLightbox']"
                                       "//input[@name='ajaxhref']/@value").extract()[0]

        meta = response.meta
        meta['product_url'] = response.url

        yield Request(specification_url, callback=self.parse_product_spec, meta=response.meta)

    def parse_product_spec(self, response):
        self.log("Parse product spec")
        hxs = HtmlXPathSelector(response)

        network_gen = hxs.select("//table[@class='attributes']/tbody"
                                 "/tr[td[contains(text(), 'Networks')]]/td[2]/text()").extract()
        if not network_gen:
            network_gen = hxs.select("//table[@class='attributes']/tbody"
                                     "/tr[td[contains(text(), 'Netze')]]/td[2]/text()").extract()
        network_gen = network_gen[0]

        if '4g' in network_gen.lower() or 'lte' in network_gen.lower():
            self.log("Found 4G device: %s" % response.meta['product_url'])
            network_gen = '4G'
        elif 'hsupa' in network_gen.lower() or 'edge' in network_gen.lower() or 'hsdpa' in network_gen.lower() \
                or 'quadband' in network_gen.lower():
            self.log("Found 3G device: %s" % response.meta['product_url'])
            network_gen = '3G'
        else:
            self.log("Found unknown network generation device: %s" % response.meta['product_url'])
            network_gen = ''

        meta = response.meta
        meta['network_gen'] = network_gen

        yield Request(meta['product_url'], callback=self.parse_product, meta=response.meta, dont_filter=True)

    def parse_product(self, response):
        self.log("Parse product")
        hxs = HtmlXPathSelector(response)

        device_name = hxs.select('//div[contains(@class, "productInfo")]/h1/text()').extract()[0]
        brand = hxs.select('//script/text()').re(r'brand: "([^"]*)"')[0]

        url = response.url

        image_url = response.meta['image_url']
        network_gen = response.meta['network_gen']

        product = {
            'device_name': device_name,
            'brand': brand,
            'url': url,
            'image_url': image_url,
            'network_gen': network_gen
        }

        response.meta['product'] = product

        for item in hxs.select('//div[@class="jsRateplanGroup"]/ul'):
            plan_name = item.select('li[@class="first"]/div/text()').extract()[0]

            per_month = item.select('li[@class="second"]/div/text()').re(r'\d*')[0]
            if not per_month:
                self.log("No per-month!!! %s %s" % (plan_name, response.url), level=log.ERROR)
                continue

            # periods
            period = '24 Months'
            one_time_charge = item.select('li[@class="seventh"][@id="jsLongDuration"]/div/text()').re(r'\d*')[0]
            try:
                self.products.append(self._make_product(response, plan_name, per_month, period, one_time_charge))
            except InvalidCategory:
                pass

            period = '12 Months'
            one_time_charge = item.select('li[@class="seventh"][@id="jsShortDuration"]/div/text()').re(r'\d*')[0]
            try:
                self.products.append(self._make_product(response, plan_name, per_month, period, one_time_charge))
            except InvalidCategory:
                pass

    def _make_product(self, response, plan_name, per_month, period, one_time_charge):
        return make_product_from_response(response, operator, channel, plan_name, per_month, period, one_time_charge)
