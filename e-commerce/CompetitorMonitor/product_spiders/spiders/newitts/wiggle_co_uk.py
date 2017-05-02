from scrapy.http import Request

from product_spiders.base_spiders.wigglespider import WiggleSpider

class WiggleSpider(WiggleSpider):
    name = 'newitts-wiggle.co.uk'

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'GBP'
    _lang_form_countryID = '1'

    do_full_run = True

    def full_run_required(self):
        return True

    def parse_product_list(self, response):
        next_page = response.xpath('//div[@id="pagerMainColumnHeader"]//a[normalize-space(text())=">"]/@href').extract()
        if next_page:
            yield Request(url=next_page[0], callback=self.parse_product_list)

        products = response.xpath('//a[@data-ga-action="Product Title"]/@href').extract()
        if products:
            for product in products:
                yield Request(url=product, callback=self.parse_product)

        categories = response.xpath('//a[@data-ga-action="Categories"]/@href').extract()
        if categories:
            for category in categories:
                yield Request(url=category, callback=self.parse_product_list)


