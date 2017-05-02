import os

from scrapy.contrib.spiders import XMLFeedSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class Reader:
    def __init__(self):
        self.data = ""

    def __call__(self, s):
        self.data += s


class AxeMusicSpider(XMLFeedSpider):
    name = 'axemusic.com-feed'
    allowed_domains = ['axemusic.com']
    start_urls = ('https://www.axemusic.com/media/feed/intelligenteye.xml',)
    itertag = 'item'

    def __init__(self, *argv, **kwgs):
        super(AxeMusicSpider, self).__init__(*argv, **kwgs)

    def parse_node(self, response, selector):
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', selector.select('./id/text()').extract())
        loader.add_value('name', selector.select('./name/text()').extract())
        loader.add_value('price', selector.select('./price/text()').extract())
        loader.add_value('category', selector.select('./category/text()').extract())
        loader.add_value('sku', selector.select('./sku/text()').extract())
        loader.add_value('url', selector.select('./url/text()').extract()[0].replace('http://', 'https://'))
        loader.add_value('image_url', selector.select('./imageurl/text()').extract()[0].replace('http://', 'https://'))
        loader.add_value('brand', selector.select('./brand/text()').extract())
        return loader.load_item()
