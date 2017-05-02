from scrapy.contrib.spiders import CSVFeedSpider

from productloader import load_product

class hagenlist_spider(CSVFeedSpider):
    name = 'hagen-list.com'
    allowed_domains = ['competitormonitor.com', 'www.competitormonitor.com']
    start_urls = ('http://competitormonitor.com/users_data/hagen-list_site.txt',)

    delimiter = ','
    headers = ['', 'name', 'price']

    def parse_row(self, response, row):
        res = {}
        name = row['name']
        split = name.split(" - ")
        sku = split[0]
        name = " - ".join(split[1:])
        url = ''
        price = row['price']
        res['url'] = url
        res['description'] = name
        res['price'] = price
        res['sku'] = sku
        return load_product(res, response)
