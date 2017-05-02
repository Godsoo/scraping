from scrapy import log
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (Product,
        ProductLoaderWithNameStrip as ProductLoader)


class BedsMonsterBedsCoUkSpider(BaseSpider):
    name = 'beds.monsterbeds.co.uk'
    allowed_domains = ['beds.monsterbeds.co.uk']

    def __init__(self, *args, **kwargs):
        super(BedsMonsterBedsCoUkSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        yield Request(
                url='http://beds.monsterbeds.co.uk/',
                callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//ul[contains(@id, "MegaMenu33220628")]//a/@href').extract():
            yield Request(
                    url=urljoin_rfc(base_url, url),
                    callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select(
                u'//div[@class="ListItemCategory"]//a/@href').extract():
            yield Request(
                    url=urljoin_rfc(base_url, url),
                    callback=self.parse_product_list)

        for url in hxs.select(
                u'//ul[@class="PagerSizeContainer"]//a/@href').extract():
            yield Request(
                    url=urljoin_rfc(base_url, url),
                    callback=self.parse_product_list)

        for url in hxs.select(
                u'//div[@class="ListItemProductInfoContainer"]//a/@href'
                ).extract():
            yield Request(
                    url=urljoin_rfc(base_url, url),
                    callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value(
                'url', response.url)
        product_loader.add_xpath(
                'name', u'//div[contains(@class,"InfoArea")]/h1/text()')
        product_loader.add_xpath(
                'sku', u'//input[@name="ErrorObjectID"]/@value')

        optid = hxs.select(u'//option[@selected]/@value').extract()
        if not optid:
            optid = ['']

        product_loader.add_value(
                'identifier',
                product_loader.get_output_value('sku') + '-' + optid[0])
        product_loader.add_xpath(
                'price', u'//*[@itemprop="price"]/text()')

        try:
            category = hxs.select(u'//a[@class="BreadcrumbItem"]/*/text()')[1].extract().strip()
            product_loader.add_value('category', category)
        except:
            pass

        img = hxs.select(
                u'//div[@class="ProductImage"]//a/img/@src').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(base_url, img))

        product = product_loader.load_item()
        product['name'] = product['name'] + response.meta.get('name', '')
        yield product

        if '&SelectedVariation=' in response.url:
            return
        for opt in hxs.select(u'//table[@class="SelectVariation"]//option'):
            url = hxs.select(
                    u'//form[@id="SelectVariationForm"]/@action'
                    ).extract()[0]
            url += '&ChangeAction=SelectSubProduct&SelectedVariation=' + opt.select(
                    './@value').extract()[0]
            url = urljoin_rfc(base_url, url)
            name = ' ' + opt.select('normalize-space(./text())').extract()[0]
            name = name.replace('PLEASE SELECT', '')
            yield Request(
                    url=url,
                    callback=self.parse_product,
                    meta={'name': name})
