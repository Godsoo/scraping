import os

from scrapy.http import Request

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.spiders.lego_usa.lego_amazon_base_spider import BaseLegoAmazonUSASpider

class LegoAmazonSpider(BaseLegoAmazonUSASpider):
    name = 'lego-usa-amazon.com-direct'
    _use_amazon_identifier = True
    amazon_direct = True
    collect_reviews = False
    review_date_format = u'%m/%d/%Y'

    user_agent = 'spd'

    skus_found = []
    errors = []

    lego_amazon_domain = 'www.amazon.com'

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'amazondirect_map_deviation.csv')
    map_screenshot_method = 'scrapy_response'
    map_screenshot_html_files = {}

    def process_collected_products(self):
        for item in super(LegoAmazonSpider, self).process_collected_products():
            yield Request(item['url'], callback=self.save_product_page_html, meta={'product': item})

    def save_product_page_html(self, response):
        product = response.meta['product']
        html_path = os.path.join(HERE, '%s.html' % product['identifier'])
        with open(html_path, 'w') as f_html:
            f_html.write(response.body)
        self.map_screenshot_html_files[product['identifier']] = html_path

        yield product

    def _collect_amazon_direct(self, product, meta):
        self._collect_best_match(product, meta['search_string'])
