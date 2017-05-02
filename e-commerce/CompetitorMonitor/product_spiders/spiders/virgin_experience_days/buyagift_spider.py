from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class BuyAGiftSpider(SecondaryBaseSpider):
    name = 'virgin_exp_days-buyagift.co.uk'
    allowed_domains = ['buyagift.co.uk', 'competitormonitor.com']
    csv_file = 'buyagift/buyagift.co.uk_products.csv'
    start_urls = ['http://www.buyagift.co.uk']
