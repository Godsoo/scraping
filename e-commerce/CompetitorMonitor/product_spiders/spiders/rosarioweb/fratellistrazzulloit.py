from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

from product_spiders.items import Product, ProductLoader

import logging
from scrapy.utils.response import get_base_url
from w3lib.url import urljoin_rfc

class FratellistrazzulloItSpider(BaseSpider):
    name = "fratellistrazzullo.it"
    allowed_domains = ["fratellistrazzullo.it"]
    start_urls = (
        'http://www.fratellistrazzullo.it/',
        'http://www.fratellistrazzullo.it/risultati.aspx?keywords=%25&pls_go=Vai'
        )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select("//div[@id='box_left_ctl03_livello_box']//table[@class='tabellaMenu']/tr/td[2]/a/@href").extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse)

        pages = hxs.select("//div[@id='box_center_span_navigazione']//a/@href").extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse)

        items = hxs.select('//td[@class="centerPagina"]//a[contains(@href, "prodotto") and not(contains(@href, ".jpg") and not(contains(@href, ".pdf")))]/@href').extract()
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_item)

    def parse_item(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        content = hxs.select("//td[@class='centerPagina']/div[@class='tabMargini']/table[@class='tabellaBoxCentrale']/form/tr[2]/td/table/tr/td[2]")
        name = content.select("//td[@class='centerPagina']/div[@class='tabMargini']/table[@class='tabellaBoxCentrale']/form/tr[1]/td/h1[@class='titolo']/text()").extract()
        if not name:
            logging.error("NO NAME!")
            return
        name = name[0]
        url = response.url

        # adding product
        price = content.select("span[@id='box_center_span_prezzo']/span[@class='prezzo']/strong/text()").extract()
        if not price:
            logging.error("NO PRICE")
            return
        price = price[0].replace(".", "").replace(",", ".")

        l = ProductLoader(item=Product(), response=response)
        l.add_xpath('identifier', '//input[@id="pid"]/@value')
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        yield l.load_item()

        items = hxs.select('//td[@class="centerPagina"]//a[contains(@href, "prodotto") and not(contains(@href, ".jpg") and not(contains(@href, ".pdf")))]/@href').extract()
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_item)
