from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class LawsonHisSpider(SecondaryBaseSpider):
    name = 'toolstop-lawson-his.co.uk'
    allowed_domains = ['lawson-his.co.uk']
    csv_file = 'ffxtools/lawson-his.co.uk_products.csv'
    start_urls = ['http://www.lawson-his.co.uk']
