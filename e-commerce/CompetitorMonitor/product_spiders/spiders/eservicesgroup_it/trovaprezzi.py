"""
E-Services IT Trovaprezzi spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4616
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from scrapy.utils.url import url_query_cleaner
from utils import extract_price_eu

class TrovaPrezzi(CrawlSpider):
    name = 'e-services.it_trovaprezzi.it'
    allowed_domains = ['trovaprezzi.it']
    start_urls = (
        'http://www.trovaprezzi.it/prezzi_fotocamere-digitali.aspx',
        'http://www.trovaprezzi.it/prezzi_obiettivi-per-fotocamere.aspx',
        'http://www.trovaprezzi.it/prezzi_cellulari.aspx',
        'http://www.trovaprezzi.it/prezzi_tablet.aspx',
        'http://www.trovaprezzi.it/prezzi_cardiofrequenzimetri.aspx',
        'http://www.trovaprezzi.it/prezzi_gps.aspx',
        'http://www.trovaprezzi.it/prezzi_orologi-polso.aspx',
        'http://www.trovaprezzi.it/prezzi_cuffie-microfoni.aspx'
        )
    
    rules = (
        Rule(LinkExtractor(restrict_css=('.child_list',
                                         '.pagination',
                                         '.product_best_prices')),
             callback='parse_products',
             follow=True),
        )

    def parse_products(self, response):
        category = response.css('.breadcrumbs').xpath('.//a/text()').extract()[1:]
        products = response.css('.listing_item')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            image_url = product.css('.listing_item_image').xpath('img/@src').extract_first()
            if not 'noimage' in image_url:
                loader.add_value('image_url', image_url)
            url = product.css('.listing_item_name').xpath('@href').extract_first()
            url = url_query_cleaner(response.urljoin(url))
            sku = url.split('/')[-1]
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)

            loader.add_value('url', url)
            loader.add_xpath('name', './/a[@class="listing_item_name"]/text()')
            loader.add_xpath('price', './/span[@class="listing_item_basic_price"]/text()')
            loader.add_value('category', category)
            shipping_cost = product.css('.listing_item_delivery_costs').xpath('text()').extract_first()
            loader.add_value('shipping_cost', extract_price_eu(shipping_cost))
            if 'Non disponibile' in product.css('.listing_item_availability').xpath('text()').extract_first():
                loader.add_value('stock', 0)
            item = loader.load_item()
            dealer = product.css('.listing_item_merchant_name').xpath('img/@alt').extract_first()
            item['metadata'] = {'Dealer': dealer}
            yield item
