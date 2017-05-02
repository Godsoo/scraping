from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class ToollineukSpider(SecondaryBaseSpider):
    name = 'toolstop-toollineuk.com'
    allowed_domains = ['toollineuk.com']
    csv_file = 'ffxtools/toollineuk.com_products.csv'
    start_urls = ['http://www.toollineuk.com']
