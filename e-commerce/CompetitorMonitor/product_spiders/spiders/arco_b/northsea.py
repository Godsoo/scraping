from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class NorthseaSpider_B(SecondaryBaseSpider):
    name = 'arco-b-northseaworkwear.com'
    allowed_domains = ['northseaworkwear.com']
    start_urls = ('http://www.northseaworkwear.com/changetaxtype/10?returnurl=%2f',)

    csv_file = 'arco_a/northseaworkwear_crawl.csv'