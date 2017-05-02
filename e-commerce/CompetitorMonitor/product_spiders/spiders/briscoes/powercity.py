import re

from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class PowerCity(Spider):
    name = 'briscoes-powercity'
    allowed_domains = ['powercity.ie']
    start_urls = ['http://www.powercity.ie']

    deduplicate_identifiers = True

    def parse(self, response):
        categories = filter(lambda u: u != '#' and './?action=' not in u,
                            response.xpath('//ul[@id="sddm"]//a/@href').extract())
        for cat in categories:
            url = response.urljoin(cat)
            yield Request(url, callback=self.parse_ajax)

    def parse_ajax(self, response):
        ajax_url = response.urljoin(
            ''.join(re.findall(r'"(\./slider271014.php.*)"',
                               response.body)[0].split('+')[::2]).replace('"', ''))
        yield Request(ajax_url, callback=self.parse_category)

    def parse_category(self, response):
        for page in set(response.xpath('//input[@id="npages"]/@value').extract()):
            url = add_or_replace_parameter(response.url, 'npages', page)
            yield Request(url, callback=self.parse_category)

        #products
        for url in response.xpath('//table/tr/td[2]//a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        flix = '//script[@type="text/javascript"]/@data-flix-%s'
        name = response.xpath('//td/div[@align="center"]/b/text()').extract()
        if not name:
            return
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name[0].strip(' ,'))
        loader.add_value('url', response.url)
        identifier = filter(lambda s: bool(s.strip()), response.xpath(flix % 'ean').extract())
        if not identifier or not identifier[0]:
            identifier = response.xpath('//b[contains(text(), "Model :")]/../text()[1]').extract()
        sku = response.xpath(flix % 'mpn').extract()
        if not sku or not sku[0]:
            sku = response.xpath('//b[contains(text(), "Model")]/../text()[1]').extract()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        price = re.findall(u'POST.+?> *&#8364;(.+?) *<', response.body)
        loader.add_value('price', price)
        loader.add_xpath('category', '//h8//a[position()>1]/text()')
        loader.add_xpath('brand', flix % 'brand')
        stock = response.xpath('//button[@value="Central Warehouse"]/../text()').extract_first()
        if not stock or 'Available' not in stock:
            loader.add_value('stock', 0)
        item = loader.load_item()
        if response.xpath('//img[@alt="Exdisplay"]'):
            item['metadata'] = {'Ex Display': 'Ex Display'}

        yield item
