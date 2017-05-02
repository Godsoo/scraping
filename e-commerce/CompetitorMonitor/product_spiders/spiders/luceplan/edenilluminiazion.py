# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, json, logging


class EdenilluminiazionSpider(BaseSpider):

    name              = "edenilluminiazion"
    start_urls        = ["http://www.edenilluminazione.org/epages/62033157.sf/it_IT/?ObjectPath=/Shops/62033157/Categories/LUCEPLAN"]
    base_url          = "http://www.edenilluminazione.org/epages/62033157.sf/it_IT/"

    download_delay    = 1


    def parse(self, response):

        hxs   = HtmlXPathSelector(response)
        links = hxs.select("//div[@id='CategoryProducts']//div[contains(@class,'ListItemProductContainer')]//a[@itemprop='url']/@href").extract()

        for link in links:
            link = self.base_url + link
            yield Request(url=link, callback=self.parse_page)

        try:
            next_page = self.base_url + hxs.select("//a[@rel='next']/@href").extract()[0]
            yield Request(url=next_page, callback=self.parse)
        except:
            pass


    def parse_page(self, response):

        hxs = HtmlXPathSelector(response)

        options_form = hxs.select("//form[@id='SelectVariationForm']")
        if options_form:
            post_url = self.base_url + options_form.select("./@action").extract()[0]
            first_options  = options_form.select(".//select[@id='SelectedVariation0']/option")
            second_options = options_form.select(".//select[@id='SelectedVariation1']/option")
            for first_option in first_options:
                first_option_value = first_option.select("./@value").extract()[0]
                first_option_name  = first_option.select("./text()").extract()[0]
                if not first_option_value:
                    continue

                if second_options:
                    for second_option in second_options:
                        second_option_value = second_option.select("./@value").extract()[0]
                        second_option_name  = second_option.select("./text()").extract()[0]

                        #== I had to split 'formdata' in two parts because of 'SelectedVariation' key which is similar for both options
                        #== we can't create a 'formdata' dict with two equal keys, that is why I add the second one later with ._body ==#
                        form_request = FormRequest(url=post_url,
                                          formdata={'SelectedVariation': '{}'.format(first_option_value)},
                                          meta={'first_option_name':   first_option_name,
                                                'first_option_value':  first_option_value,
                                                'second_option_name':  second_option_name,
                                                'second_option_value': second_option_value,
                                                'options': True},
                                          callback=self.parse_form_response,
                                          dont_filter=True)
                        form_request._body += '&SelectedVariation={}&ChangeAction=SelectSubProduct'.format(second_option_value)
                        yield form_request
                else:
                    yield FormRequest(url=post_url, 
                                      formdata={'ChangeAction':      'SelectSubProduct',
                                                'SelectedVariation': '{}'.format(first_option_value)},
                                      meta={'first_option_name':  first_option_name,
                                            'first_option_value': first_option_value,
                                            'options': True},
                                      callback=self.parse_form_response,
                                      dont_filter=True)
        else:
            for product in self.parse_form_response(response):
                yield product





    def parse_form_response(self, response):

        hxs = HtmlXPathSelector(response)
        url = response.url

        identifier = ''.join(hxs.select("//form[@id='basketForm_standalone']//button[@name='AddToBasket']/@data-productid").extract())
        name  = hxs.select("//h1[@itemprop='name']/text()").extract()[0]
        if not identifier:
            return
        if response.meta.get('options'):

            if response.meta.get('second_option_name'):
                option_name  = response.meta.get('first_option_name')  + ' ' + response.meta.get('second_option_name')
                option_value = response.meta.get('first_option_value') + ' ' + response.meta.get('second_option_value')
            else:
                option_name  = response.meta.get('first_option_name')
                option_value = response.meta.get('first_option_value')

            option_name  = option_name.strip()
            option_value = option_value.strip()
            identifier   = ''.join(hxs.select("//form[@id='basketForm_standalone']//button[@name='AddToBasket']/@data-productid").extract()) + ' ' + option_value
            name  = hxs.select("//h1[@itemprop='name']/text()").extract()[0] + ' ' + option_name
        image_url = ''.join(hxs.select("//meta[@name='og:image']/@content").extract())

        price = ''.join(hxs.select("//meta[@itemprop='price']/@content").extract()).strip()
        stock = 1 if price else 0
        shipping_price = 7 if price <= 100 else 0

        category = ''.join(hxs.select("//td[text()='TIPOLOGIA']/following::td[1]/text()").extract()).strip()
        if not category:
            category = ''.join(hxs.select("//td[text()='TYPE']/following::td[1]/text()").extract()).strip()

        sku = ''.join(hxs.select("//td[text()='CODICE']/following::td[1]/text()").extract()).strip()
        if not sku:
            sku = ''.join(hxs.select("//td[text()='CODE']/following::td[1]/text()").extract()).strip()

        brand = 'Luceplan'
        
        l = ProductLoader(item=Product(), response=response)

        l.add_value('brand', brand)
        l.add_value('name', name)
        l.add_value('image_url', image_url)
        l.add_value('url', url)
        l.add_value('stock', stock)
        l.add_value('sku', sku)
        l.add_value('identifier', identifier)
        l.add_value('category', category)
        l.add_value('price', price)

        yield l.load_item()