from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class ToolStopSpider(SecondaryBaseSpider):
    name = 'toolstop-toolstop.co.uk'
    allowed_domains = ['toolstop.co.uk']
    csv_file = 'ffxtools/toolstop.co.uk_products.csv'
    start_urls = ['http://www.toolstop.co.uk/?gl=gb&currency=GBP']
