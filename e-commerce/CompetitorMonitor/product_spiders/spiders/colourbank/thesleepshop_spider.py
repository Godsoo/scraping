# -*- coding: utf-8 -*-
from decimal import Decimal
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price2uk
from scrapy.spider import BaseSpider

def multiply(lst):
    if not lst:
        return [(0, '')]

    while len(lst) > 1:
        result = []
        for price0, name0 in lst[0]:
            for price1, name1 in lst[1]:
                result.append((float(price0) + float(price1), name0 + ' ' + name1))
        lst = [result] + lst[2:]
    return lst[0]


def remove_extension(filename):
    return filename.replace('.gif', '').replace('.jpg', '').replace('.jpeg', '').replace('.png', '')


class TheSleepShopSpider(BaseSpider):
    name = "colourbank-thesleepshop.co.uk"
    allowed_domains = ('thesleepshop.co.uk', )
    start_urls = ('http://www.thesleepshop.co.uk/', )

    def start_requests(self):
        yield Request('http://www.thesleepshop.co.uk/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select(u'//div[@id="menubar_top"]//a'):
            url = urljoin_rfc(get_base_url(response), cat.select(u'./@href').extract()[0].strip())
            yield Request(url, callback=self.parse_product_list,
                          meta={'category': cat.select(u'normalize-space(./text())').extract()[0]})

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        if hxs.select(u'//input[@name="PAGE" and @value="PRODUCT"]'):
            for x in self.parse_product(response):
                yield self.add_shipping_cost(x)
        else:
            for url in hxs.select(u'//div[@id="rt_col"]//table//a/@href').extract():
                url = urljoin_rfc(get_base_url(response), url.strip())
                yield Request(url, callback=self.parse_product_list, meta=response.meta)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)

        opt_groups = []
        inside = False
        lst = ''
        for line in response.body.split('\n'):
            if line.startswith('perms[\''):
                inside = True
                lst = ''
            elif line.startswith('];'):
                if lst:
                    opts = eval('[' + lst + ']')
                    # XXX http://www.thesleepshop.co.uk/acatalog/4ft6_Double_Kyoto_Memphis_Futon.html#a11717
                    # second option has "Deluxe Mattress" twice with different additional price
                    # however price calculation ignores second addition price (uses first value)
                    filtered_opts = []
                    for price, name in opts:
                        if not [name for pn in filtered_opts if pn[1] == name]:
                            filtered_opts.append([price, name])
                    opt_groups.append(filtered_opts)
                inside = False
            elif inside:
                lst += line

        identifier = hxs.select('//form//input[contains(@name, "Q_")]/@name').re(r'Q_(.*)$')[0]

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h3[@class="product"]/text()')
        product_loader.add_xpath('name', u'//span[@class="product"]/text()')
        product_loader.add_value('sku', identifier)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('category', response.meta.get('category'))

        product_loader.add_css('price', '.discprice::text')
        price_reg = response.xpath('//div[@id="price_inside"]//span//text()').extract_first() or response.xpath('//div[@id="price_inside"]//span/@ppraw').extract_first()
        price_reg = extract_price2uk(price_reg)
        product_loader.add_value('price', price_reg)
        product_loader.add_value('price', '')
        
        discount = product_loader.get_output_value('price')/price_reg

        img = hxs.select(u'//div[@class="slides_control"]/a/img/@src').extract()
        if not img:
            img = hxs.select(u'//div[@class="image_product"]//img/@src').extract()
        product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        brand_logo = hxs.select(u'//h3[@class="product"]/../img/@src').extract()
        if not brand_logo:
            brand_logo = hxs.select(u'//h3[@class="product"]/img/@src').extract()

        brands = {
            '6thsense.jpg': '6th sense',
            'bentley.gif': 'bentley',
            'birlea.gif': 'birlea',
            'blank.gif': '',
            'brand': '',
            'Breasley.gif': 'breasley',
            'buoyant.jpg': 'buoyant',
            'cro.gif': 'cro',
            'cumfilux.gif': 'cumfilux',
            'dt.gif': 'dt',
            'dunlopillo.gif': 'dunlopillo',
            'durabeds.gif': 'durabeds',
            'easycomfort.gif': 'easy comfort',
            'friendship_mill.gif': 'friendship mill',
            'Furmanac.gif': 'furmanac',
            'gainsborough.gif': 'fainsborough',
            'gleneagle.gif': 'gleneagle',
            'harlequin.gif': 'harlequin',
            'harmony.gif': 'harmony',
            'healthbeds.gif': 'healt beds',
            'highgate.gif': 'highgate',
            'hypnos.gif': 'hypnos',
            'jay-be.gif': 'jay be',
            'julianbowenlogo.jpg': 'julian bowen',
            'kaymed.gif': 'kaymed',
            'komfi.gif': 'komfi',
            'kyoto.gif': 'kyoto',
            'limelight.gif': 'limelight',
            'metalbeds.gif': 'metalbeds',
            'millbrook.gif': 'millbrook',
            'myers.gif': 'myers',
            'nd.gif': 'newdesign',
            'nestledown.gif': 'nestledown',
            'obc.gif': 'original bedstead',
            'Protectabed.gif': 'protectabed',
            'rauch.gif': 'rauch',
            'relaxsan.gif': 'relaxsan',
            'relyon.gif': 'relyon',
            'rest_assured.gif': 'rest assured',
            'richman.gif': 'richman',
            'sealy.gif': 'sealy',
            'shakespeare.gif': 'shakespeare',
            'silentnight.gif': 'silentnight',
            'sleepeezee.gif': 'sleepeezee',
            'sleepshaper.gif': 'sleepshaper',
            'sleepyvalley.gif': 'sleepyvalley',
            'slumberland.gif': 'slumberland',
            'staples.gif': 'staples',
            'steens.gif': 'steens',
            'swanglen.gif': 'swanglen',
            'sweetdreams.gif': 'sweetdreams',
            'tss.gif': 'the sleep shop',
            'verona.jpg': 'verona',
            'welcome.gif': 'welcome furniture',
        }
        product_loader.add_value('brand', brands.get(brand_logo[0], remove_extension(brand_logo[0])))
        product = product_loader.load_item()
        for opt_price, opt_name in multiply(opt_groups):
            prod = Product(product)
            prod['name'] = (prod['name'] + ' ' + opt_name).strip()
            try:
                prod['price'] = (Decimal(prod['price']) + Decimal(opt_price)*discount).quantize(Decimal('1.00'))
            except TypeError:
                prod['price'] = Decimal(0)
            prod['identifier'] = prod['identifier'] + ':' + opt_name
            yield prod

    def add_shipping_cost(self, item):
        if not item['price'] or Decimal(item['price']) < 300:
            if item['category'].upper() == 'ACCESSORIES':
                item['shipping_cost'] = 5.95
            else:
                item['shipping_cost'] = 19
        return item
