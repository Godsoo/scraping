from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
from urllib import urlencode
import json
import re


class BikeDiscountDeSpider(BigSiteMethodSpider):
    name = 'bike-discount.de'
    allowed_domains = ['bike-discount.de']
    website_id = 487809

    start_urls = ['http://www.bike-discount.de/en/']

    new_system = True
    old_system = False

    idents = []

    def _start_requests(self):
        yield Request('http://www.bike-discount.de/en/buy/nutrixxion-iso-refresher-citrus-700g-free-bottle-600ml-215558', callback=self.parse_product)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[@id="main-nav-wrapper"]//a/@href').extract():
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product_list)

        yield Request('http://www.bike-discount.de/sitemap_www_bike-discount_de_en.xml',
                      callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        urls = re.findall(r'(http://([\w\.-]+/?)+)', response.body)

        for url in urls:
            yield Request(url[0], callback=self.parse_product)

    def parse_product_list(self, response):
        try:
            hxs = HtmlXPathSelector(response)
        except:
            try:
                data = json.loads(response.body)
                hxs = HtmlXPathSelector(text=data['data'])
            except:
                return

        products = hxs.select(u'//a[@itemprop="url"]/@href').extract()

        for url in products:
            try:
                url = urljoin_rfc(get_base_url(response), url)
            except:
                url = urljoin_rfc('http://www.bike-discount.de', url)
            yield Request(url, callback=self.parse_product)

        if products:
            next_page = response.meta.get('page', 0) + 1
            json_next_url = 'http://www.bike-discount.de/json.php?service=getProductsContent&page=%(page)s&order_by=ranking'
            params = dict(zip(hxs.select('//form[@id="frmSearchDetails"]//input/@name').extract(), hxs.select('//form[@id="frmSearchDetails"]//input/@value').extract()))
            json_next_url += '&' + urlencode(params)

            yield Request(json_next_url % {'page': next_page}, meta={'page': next_page}, callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        try:
            brand_name = hxs.select('//*[@itemprop="brand"]/text()').extract()[0]
            name = hxs.select('//h1[@class="product-title"]/span/text()').extract()[-1].strip()
        except:
            return

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_value('name', brand_name + ' ' + name)
        product_loader.add_xpath('sku', u'//div[@class="additional-product-no" and contains(text(), "Manufacturer Item no.")]', re=r'Manufacturer Item no\. (.*)')
        product_loader.add_xpath('identifier', u'//body/@data-vw-id')

        price = hxs.select('//div[contains(@class, "artikel-detail")]//*[@itemprop="price"]/text()').extract()
        if not price:
            price = ''
        else:
            price = price[0]

        product_loader.add_value('price', price.replace('.', '').replace(',', '.'))

        category = hxs.select('//nav[@id="breadcrumb"]//a/text()').extract()[-1]

        product_loader.add_value('category', category)

        product_loader.add_value('brand', brand_name.strip())

        try:
            image_url = urljoin_rfc(base_url, hxs.select('//img[@itemprop="image"]/@src').extract()[0])
            product_loader.add_value('image_url', image_url)
        except:
            pass
        product = product_loader.load_item()
        options = hxs.select('//div[@id="variantselector"]//tr[@class="variant"]')
        if options:
            for opt in options:
                p = Product(product)
                try:
                    p['name'] = p['name'] + ' ' + opt.select(u'.//td[2]/label/text()').extract()[0]
                except IndexError:
                    # No option name extension 
                    pass
                p['identifier'] = p['identifier'] + '-' + opt.select(u'.//input/@value').extract()[0]
                if p['identifier'] not in self.idents:
                    self.idents.append(p['identifier'])
                    yield p
        else:
            if product['identifier'] not in self.idents:
                self.idents.append(product['identifier'])
                yield product

    def closing_parse_simple(self, response):
        for item in super(BikeDiscountDeSpider, self).closing_parse_simple(response):
            if item['identifier'] not in self.idents:
                yield item
