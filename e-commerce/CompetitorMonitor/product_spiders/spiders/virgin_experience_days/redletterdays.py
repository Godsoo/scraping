from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class RedLetterDaysSpider(SecondaryBaseSpider):
    name = 'virgin_exp_days-redletterdays.co.uk'
    allowed_domains = ['redletterdays.co.uk', 'competitormonitor.com']
    csv_file = 'buyagift/redletterdays.co.uk_products.csv'
    start_urls = ['http://www.redletterdays.co.uk']
