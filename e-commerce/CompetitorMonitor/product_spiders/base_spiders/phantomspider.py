from scrapy.spider import BaseSpider
from product_spiders.phantomjs import PhantomJS
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

class PhantomSpider(BaseSpider):

    def __init__(self, *args, **kwargs):
        super(PhantomSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browser = PhantomJS()

    def spider_closed(self, spider):
        if hasattr(super(PhantomSpider, self), 'spider_closed'):
            if callable(super(PhantomSpider, self).spider_closed):
                super(PhantomSpider, self).spider_closed(spider)

        self._browser.close()
