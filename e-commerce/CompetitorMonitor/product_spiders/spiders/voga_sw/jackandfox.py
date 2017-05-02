from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class JackAndFox(SecondaryBaseSpider):
    name = 'voga_sw-jackandfox.com'
    allowed_domains = ['www.jackandfox.com']
    start_urls = ('http://www.jackandfox.com/catalog/seo_sitemap/category/',)

    csv_file = 'voga_uk/jackandfox_products_primary.csv'
