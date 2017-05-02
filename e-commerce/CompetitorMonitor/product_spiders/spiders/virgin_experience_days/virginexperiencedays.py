from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class VirginExperienceDaysSpider(SecondaryBaseSpider):
    name = 'virgin_exp_days-virginexperiencedays.co.uk'
    allowed_domains = ['virginexperiencedays.co.uk', 'competitormonitor.com']
    csv_file = 'buyagift/virginexperiencedays.co.uk_products.csv'
    start_urls = ['http://www.virginexperiencedays.co.uk']
