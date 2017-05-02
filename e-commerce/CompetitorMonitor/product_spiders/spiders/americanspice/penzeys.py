from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items \
import Product, ProductLoaderWithNameStrip as ProductLoader


class PenzeysSpider(BaseSpider):
    name = 'penzeys.com'
    allowed_domains = ['penzeys.com']
    start_urls = ('http://www.penzeys.com/cgi-bin/penzeys/shophome.html',)

    download_delay = 60

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        catlistcombo = hxs\
            .select('//form[@name="penzey"]/select/option/text()').extract()

        catlisturls = hxs\
            .select('//div[@id="wrapper"]/script/text()')\
            .re(r'location.*"(http.*\.html).*"')

        for caturl in catlisturls:
            current_category = catlistcombo[catlisturls.index(caturl) + 1]
            yield Request(caturl, self.parse_products,
                          meta={'category': current_category})

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)

        itemsurls = hxs.select('//ul[@id="items"]/li/a/@href').extract()

        if itemsurls:
            for itemurl in itemsurls:
                yield Request(itemurl, self.parse_products,
                              meta={'category': response.meta.get('category',
                                                                  None)})

        items_rows = hxs.select('//form//table/tr/td/table/tr/td/table/tr/td')
        product_name = None

        if not items_rows:
            items_rows = hxs.select('//form//table/tr')
        else:
            product_name = hxs.select('//h2/text()').extract()

        for item in items_rows:
            identifier = item\
                .select('.//input[contains(@name, "mv_order_item")]/@value')\
                .extract()
            columns = item.select('./td')
            if identifier:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', identifier)
                loader.add_value('sku', identifier)
                loader.add_value('url', get_base_url(response))
                loader.add_value('category', response.meta.get('category',
                                                               None))

                try:
                    price = item\
                        .select('.//td/text()').re(r'\$.+').pop().strip()
                except:
                    try:
                        price = item\
                            .select('./td//font/text()').re(r'\$.+').pop()\
                            .strip()
                    except:
                        price = items_rows[items_rows.index(item) - 1]\
                            .select('font/b/text()').extract()
                loader.add_value('price', price)
                if not product_name:
                    name = None
                    if len(columns) == 3 or \
                      (len(columns) == 4 and
                       not columns[-1].select('.//input').extract()):
                        try:
                            name = columns[0]\
                                .select('.//a/text()').extract().pop().strip()
                        except:
                            name = columns[0]\
                                .select('text()').extract().pop().strip()
                    elif len(columns) >= 4:
                        name = ' '.join(w.strip() for w in columns[1]
                                        .select('.//font/text()').re(r'.+'))
                    if name:
                        loader.add_value('name', name)
                    else:
                        loader.add_value('name', response.meta.get('category',
                                                                   None))
                else:
                    loader.add_value('name', product_name)

                yield loader.load_item()
