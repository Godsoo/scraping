# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.http import Request, FormRequest
import re, datetime, string
from scrapy.utils.response import get_base_url
from urlparse import urljoin


class LambinSpider(BaseSpider):

    name = "lambin.fr"
    allowed_domains = ["lambin.fr"]
    start_urls = ["http://www.lambin.fr/"]


    def parse(self, response):
        hxs = HtmlXPathSelector(response=response)
        brands = hxs.select("//select[@id='manufacturer_list']//option")[2:]

        for brand in brands:
            brand_name = brand.select("./text()").extract()[0]
            brand_id = brand.select("./@value").extract()[0]
            yield Request(
                url="http://www.lambin.fr/search.php?ml={}&envoyer=OK".format(brand_id),
                meta={'brand_name': brand_name},
                callback=self.parse_brand
            )
        
        for url in hxs.select('//ul[@id="main-navigation"]//a/@href').extract():
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        for url in hxs.select('//h2[@itemprop="name"]/a/@href').extract():
            yield Request(url, callback=self.parse_item)
        
        next_page = hxs.select("//li[@id='pagination_next']//a/@href").extract()
        if next_page:
            yield Request(urljoin(base_url, next_page[0]), callback=self.parse_category)
            
    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response=response)
        items = hxs.select("//ul[@id='product_list']/li/p[@class='product-img']/a/@href").extract()

        brand_name = response.meta['brand_name']

        for item in items:
            yield Request(item, meta={'brand_name': brand_name}, callback=self.parse_item)

        # == Look for the 'next page' button ==#
        try:
            next_page = "http://www.lambin.fr" + hxs.select("//li[@id='pagination_next']//a/@href").extract()[0]
            yield Request(next_page, meta={'brand_name': brand_name}, callback=self.parse_brand)
        except:
            pass

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)
        l = ProductLoader(item=Product(), response=response)

        name = hxs.select("//h1[@itemprop='name']/text()").extract()[0].title()
        price = hxs.select('//script/text()').re("productPrice=(\d.+?);")

        brand = hxs.select('//div[contains(@class, "logo-manufacturer")]/img/@alt').extract()[:1]

        categories = hxs.select('//span[@class="navigation_page"]//a/span[@itemprop="title"]/text()').extract()

        image_url = hxs.select('//div[@id="image-block"]//img/@src').extract()

        sku = hxs.select('//script/text()').re("productReference='(.+?)'")

        metadata = {'reviews': []}

        comments_blocks = hxs.select("//div[@id='gsr']/div[@class='review-line']")
        for comments_block in comments_blocks:
            tmp_dict = {'date': '', 'rating': '', 'full_text': '', 'url': ''}
            comment = comments_block.select(".//p[@itemprop='description']/text()").extract()

            tmp_dict['full_text'] = ''.join(comment).strip().replace('--', '').replace('\n', '').strip()
            tmp_dict['date'] = ''.join(comments_block.select(".//div[@class='gsrReviewLineName']/text()").extract())

            try:
                months = {'janvier':   'January',
                          'février':   'February',
                          'mars':      'March',
                          'avril':     'April',
                          'mai':       'May',
                          'juin':      'June',
                          'juillet':   'July',
                          'août':      'August',
                          'juil':      'July',
                          'septembre': 'September',
                          'octobre':   'October',
                          'novembre':  'November',
                          'décembre':  'December'}

                exclude = set(string.punctuation)

                tmp_dict['date'] = tmp_dict['date'].lower().strip().encode('utf-8')
                tmp_dict['date'] = ''.join(ch for ch in tmp_dict['date'] if ch not in exclude)

                for k, v in months.iteritems():
                    tmp_dict['date'] = tmp_dict['date'].replace(k, v)

                tmp_dict['date'] = re.findall(re.compile('(\d.*)'), tmp_dict['date'])[0].strip()
                tmp_dict['date'] = datetime.datetime.strptime(tmp_dict['date'], '%d %B %Y').strftime('%d/%m/%Y')

            except:
                tmp_dict['date'] = ''
                #continue

            tmp_dict['url'] = response.url

            try:
                tmp_dict['rating'] = int(comments_block.select('.//div[@class="review-line-rating"]/input[@checked]/@value').extract()[0])
            except:
                continue

            metadata['reviews'].append(tmp_dict)


        identifier = hxs.select('//script/text()').re("id_product=(.+?);")


        l.add_value('name', name)
        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('price', price)
        l.add_value('brand', brand)
        l.add_value('identifier', identifier)
        l.add_value('sku', sku)
        l.add_value('category', categories)


        item = l.load_item()

        item['metadata'] = metadata

        yield item
