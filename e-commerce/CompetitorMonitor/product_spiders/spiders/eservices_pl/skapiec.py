"""
E-Services PL Skapiec spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4617
"""
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price_eu
from operator import itemgetter

class Skapiec(CrawlSpider):
    name = 'e-services.pl-skapiec.pl'
    allowed_domains = ['skapiec.pl']
    start_urls = (
        'http://www.skapiec.pl/foto.html',
        'http://www.skapiec.pl/cat/26136-smartfony.html',
        'http://www.skapiec.pl/cat/20-tablety.html',
        'http://www.skapiec.pl/cat/17/1.10',
        'http://www.skapiec.pl/cat/215-glosniki-mobilne.html',
        'http://www.skapiec.pl/cat/2744-smartwatch.html',
        'http://www.skapiec.pl/cat/2289-zegarki-sportowe.html',
        'http://www.skapiec.pl/szukaj/3752/dji'
        )
    
    rules = (
        Rule(LinkExtractor(
            restrict_css=(
                '.categories-list',
                '.numeric-list'
                ),
            allow_domains='skapiec.pl'
            )),
        Rule(LinkExtractor(allow='.+cat\/.+\/comp.+', restrict_css='.products', allow_domains='skapiec.pl'),
             callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        sku = response.url.split('/')[-1]
        loader.add_value('url', response.url)
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        category = response.css('.breadcrumbs').xpath('.//a/text()').re('\S+.*\S')
        loader.add_value('category', category[1:])
        loader.add_xpath('brand', '//a[@itemprop="brand"]/text()')
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@pagespeed_lazy_src')
        
        integers = response.css('.offers-list .price').xpath('text()').extract()
        integers = [int(n.replace(' ', '').replace(',', '')) for n in integers]
        fractions = response.css('.offers-list .price').xpath('sup/text()').extract()
        fractions = [int(s) for s in fractions]
        shippings = response.css('.offers-list  .price-container').xpath('span[1]/text()').re('[\w\s]+')
        shippings = [s.replace(' ','') for s in shippings]
        dealers_id = response.css('.offers-list').xpath('ul/li/@data-dealer-id').extract()
        dealers = zip(integers, fractions, shippings, dealers_id)
        dealers.sort(key=itemgetter(0, 1, 2))
        best_dealer = dealers[0]
        
        loader.add_value('price', best_dealer[0] + best_dealer[1] * 0.01)
        dealer = response.xpath('//li[@data-dealer-id="%s"]//img/@alt' %best_dealer[-1]).extract_first() or  response.xpath('//li[@data-dealer-id="%s"]//*[contains(@class, "shop-name")]/text()' %best_dealer[-1]).extract_first()
        loader.add_value('dealer', dealer.strip())
        yield loader.load_item()
