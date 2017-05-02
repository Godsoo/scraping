from scrapy.http import Request, HtmlResponse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from productloader import load_product


class Outillage_spider(BaseSpider):
    name = 'outillage-online.fr'
    allowed_domains = ['outillage-online.fr', 'www.outillage-online.fr']
    start_urls = ('http://www.outillage-online.fr/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = ['http://www.outillage-online.fr/promotions',
                      'http://www.outillage-online.fr/accessoires-et-consommables',
                      'http://www.outillage-online.fr/outillage-a-main',
                      'http://www.outillage-online.fr/mobilier-atelier-et-rangement',
                      'http://www.outillage-online.fr/outillage-electroportatif',
                      'http://www.outillage-online.fr/outillage-stationnaire',
                      'http://www.outillage-online.fr/nettoyage-et-entretien-1',
                      'http://www.outillage-online.fr/levage-et-manutention',
                      'http://www.outillage-online.fr/protection-individuelle',
                      'http://www.outillage-online.fr/exterieurs-et-jardin',
                      'http://www.outillage-online.fr/peinture-et-revetements-des-murs',
                      'http://www.outillage-online.fr/outillage-metier-et-projet',
                      'http://www.outillage-online.fr/marques',
                      ]

        categories += hxs.select('//div[@id="nav"]//a/@href').extract()

        for url in categories:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_category)

    def parse_category(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta

        # categories
        category_urls = hxs.select(
                '//ul[@class="bare-list"]/li/a/@href').extract()
        category_urls += hxs.select(
                '//div[@class="sub marques"]//a/@href').extract()

        for category_url in category_urls:
            yield Request(
                    url=category_url,
                    callback=self.parse_category)

        # categories2
        category2_urls = hxs.select(
                '//div[@class="block-content"]/ul[@class="level-2"]'
                '/li/a/@href').extract()
        for category2_url in category2_urls:
            yield Request(
                    url=category2_url,
                    callback=self.parse_category)

        # next page
        next_pages = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next_pages:
            for page in next_pages:
                yield Request(
                        url=urljoin_rfc(base_url, page),
                        meta=meta,
                        callback=self.parse_category)

        # products
        products = hxs.select('//li[contains(@class, "item")]')
        for p in products:
            try:
                name = p.select(
                                './/h2[@class="product-name"]/a/text()'
                                )[0].extract().strip()
            except:
                continue
            else:
                res = {}
            url = p.select(
                    './/h2[@class="product-name"]/a/@href'
                    )[0].extract().strip()
            price = "".join(p.select(
                    './/div[@class="price-box"]'
                    '/span[@class="regular-price"]/span[@class="price"]'
                    '/text()').re(r'([0-9\,\. ]+)')).strip()
            if not price:
                price = "".join(p.select(
                        './/div[@class="price-box"]'
                        '/p[@class="special-price"]/span[@class="price"]'
                        '/text()').re(r'([0-9\,\. ]+)')).strip()
            image = p.select('.//a[@class="product-image"]/img/@src').extract()
            if image:
                res['image_url'] = image[0]
            category = hxs.select('//div[@class="breadcrumbs"]/ul/li/strong/text()').extract()
            if category:
                res['category'] = category[-1]
                try:
                    cat_type = hxs.select('//div[@class="breadcrumbs"]/ul/li/@class').extract()[-1]
                    if cat_type == 'manufacturer':
                        res['brand'] = category
                except:
                    pass
            else:
                category = hxs.select('//div[contains(@class, "category-title")]//h1/text()').extract()
                if category:
                    res['category'] = category[0]
            res['identifier'] = p.select('.//a[@class="link-compare"]/@href').re(r'/add/product/(\d+)/')[0]
            res['url'] = url
            res['description'] = name
            res['price'] = price
            yield Request(url, callback=self.parse_product, meta=res)

    def parse_product(self, response):
        if 'destock' in response.url:
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        res = response.meta
        brand = hxs.select('//tr[th/text()="Marque"]/td/text()').extract()
        res['brand'] = brand[0] if brand else ''
        res['stock'] = 1
        yield load_product(res, response)
