from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
import re
from decimal import Decimal


class UnlimitedTelecomSpider(BaseSpider):
    name = u'unlimited-telecom.fr'
    allowed_domains = [u'www.unlimited-telecom.fr', u'www.unlimited-telecom.com']
    start_urls = [
        u'http://www.unlimited-telecom.com/en/sitemap',
        u'http://www.unlimited-telecom.fr/en/sitemap'
    ]

    # download_delay = 0.1

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        xpath = '//div[@class="categTree"]//a[contains(substring-after(@href, "unlimited-telecom"),"-") and not(contains(@href, "content")) and not(contains(@href, "contact-us"))]/@href'
        categories = hxs.select(xpath).extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            # Request all products to be listed. Set number of products parameter to enough high
            yield Request(url + '?n=1000', callback=self.parse_category)

        categories = hxs.select("//div[@id='_menu']//a/@href").extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            # Request all products to be listed. Set number of products parameter to enough high
            yield Request(url + '?n=1000', callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        sub_categoreis_xpath = '//div[@id="subcategories"]//li/a[2]/@href'
        products_xpath = '//ul[@id="product_list"]//h3/a/@href'

        sub_categories = hxs.select(sub_categoreis_xpath).extract()

        for category in sub_categories:
            url = urljoin_rfc(get_base_url(response), category)
            # Request all products to be listed. Set number of products parameter to enough high
            yield Request(url + '?n=1000', callback=self.parse_category)

        products = hxs.select(products_xpath).extract()
        for url in products:
            yield Request(url, callback=self.parse_product)

        next_page = hxs.select('//li[@id="pagination_next"]/a/@href').extract()
        if next_page:
            url = next_page[0]
            yield Request(url, callback=self.parse_category)

    def parse_product_base(self, response , hxs):

        # self.log("WARNING parse_product_base")

        base_url = get_base_url(response)
        product_url = urljoin_rfc(base_url, response.url)

        name_xpath = '//div[@id="primary_block"]/h1//text()'
        name = hxs.select(name_xpath).extract().pop().strip()

        image_xpath = '//div[@id="image-block"]/img/@src'
        image = hxs.select(image_xpath).extract().pop()
        image_url = urljoin_rfc(base_url, image)

        breadcrumb = hxs.select('//div[@class="breadcrumb"]/a[last()]/text()').extract()
        if len(breadcrumb) > 0:
            category = breadcrumb.pop().strip()
        else:
            category = 'No category'


        price = hxs.select('//span[@id="our_price_display"]//text()').extract().pop()
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', product_url)
        loader.add_value('name', name)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price.replace(' ', '').replace(',', '.'))
        loader.add_value('category', category)
        loader.add_xpath('sku', '//p[@id="product_reference"]/span/text()')
        loader.add_xpath('identifier', '//form//input[@name="id_product"]/@value')
        return loader.load_item()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name_xpath = '//div[@id="primary_block"]/h1//text()'
        image_xpath = '//div[@id="image-block"]/img/@src'

        breadcrumb_xpath = '//div[@class="breadcrumb"]/a[last()]/text()'

        breadcrumb = hxs.select(breadcrumb_xpath).extract()
        if len(breadcrumb) > 0:
            category = breadcrumb.pop().strip()
        else:
            category = 'No category'

        name = hxs.select(name_xpath).extract().pop().strip()
        image = hxs.select(image_xpath).extract().pop()
        product_url = urljoin_rfc(base_url, response.url)
        image_url = urljoin_rfc(base_url, image)

        currencyRate = re.search('var currencyRate\D+([\d\.]+)', response.body)
        if currencyRate:
            currencyRate = Decimal(currencyRate.group(1))
        else:
            currencyRate = 1

        productPriceTaxExcluded = re.search("var productPriceTaxExcluded\D+([\d\.]+)", response.body)
        if productPriceTaxExcluded:
            productPriceTaxExcluded = Decimal(productPriceTaxExcluded.group(1))
        else:
            productPriceTaxExcluded = 0

        idDefaultImage = re.search('var idDefaultImage = (\d+)', response.body)
        if idDefaultImage:
            idDefaultImage = idDefaultImage.group(1)

        if response.url.find("unlimited-telecom.fr") != -1:

            if re.search('addCombination.*?;', response.body):

                # self.log("WARNING options found")
                # here we parse option tags for more product options.
                option_value_xpath = '//div[@id="attributes"]//select/option/@value'
                option_values = hxs.select(option_value_xpath).extract()
                option_text_xpath = '//div[@id="attributes"]//select/option//text()'
                option_texts = hxs.select(option_text_xpath).extract()

                # build the lookup table.
                options = {}
                for i in range(len(option_values)):
                    options[option_values[i]] = option_texts[i]

                for x in re.finditer('addCombination.*?;', response.body):
                    s = x.group(0).split(',')
                    offset = Decimal(s[-6])

                    # determining place of options keys
                    option_key_start = 1
                    option_key_end = len(s) - 7

                    # parsing option keys
                    option_texts = []
                    opt = ''
                    for i in range(option_key_start, option_key_end):
                        try:
                            opt = re.sub('[^\d]+', '', s[i])
                            option_text = options[opt]
                        except:
                            pass
                        if len(option_text) > 0:
                            option_texts.append(option_text.strip())

                    price = productPriceTaxExcluded + offset * currencyRate
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('url', product_url)
                    loader.add_value('name', name + ' ' + ' '.join(option_texts))

                    image_id = s[-4].strip(" '")

                    if image_id != idDefaultImage:
                        loader.add_value('image_url', image_url.replace('-' + idDefaultImage + '-', '-' + image_id + '-'))
                    else:
                        loader.add_value('image_url', image_url)

                    loader.add_value('price', price)
                    loader.add_value('category', category)
                    loader.add_value('identifier', '%s_%s' % (s[-3].strip("' "), opt))
                    loader.add_value('sku', s[-3].strip("' "))
                    yield loader.load_item()

                return
            else:
                # self.log("WARNING options not found")
                prod = self.parse_product_base(response, hxs)
                if prod:
                    yield prod
                return;

        elif response.url.find("unlimited-telecom.com") != -1:

            prod = self.parse_product_base(response, hxs)
            if prod:
                yield prod
            return
        else:
            self.log("ERROR unknown url: " + response.url)
            return

