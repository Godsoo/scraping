# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re



class JardiforetSpider(BaseSpider):

    name = "jardiforet.com"
    allowed_domains = ["jardiforet.com"]
    start_urls = ["http://www.jardiforet.com/catalog/seo_sitemap/category"]


    def parse(self, response):

        hxs = HtmlXPathSelector(response=response)

        # == Here we we extract links for all categories and making a dict of 1lvl categories ==#
        first_lvl_cats = {}
        tmp_cat_list = []
        categories = list(reversed(hxs.select("//ul[@class='sitemap']/li")))
        last_cat_id = ''


        # == magic, don't touch ==#
        for category in categories:

            category_raw = category.select("./@class").extract()[0]
            category_id = category.select("./@class").extract()[0][-1]
            category_name = category.select("./a/text()").extract()[0]
            category_href = category.select("./a/@href").extract()[0]

            if not last_cat_id:
                if category_id == '0':
                    first_lvl_cats[category_name] = [category_href]
                    last_cat_id = category_id
                else:
                    tmp_cat_list.append(category_href)
                    last_cat_id = category_id
            else:
                if category_id == '0' and tmp_cat_list:
                    first_lvl_cats[category_name] = tmp_cat_list
                    tmp_cat_list = []
                    tmp_cat_list[:] = []
                    last_cat_id = category_id
                elif category_id == '0' and not tmp_cat_list:
                    first_lvl_cats[category_name] = [category_href]
                    last_cat_id = category_id
                elif category_id > last_cat_id or category_id == last_cat_id:
                    tmp_cat_list.append(category_href)
                    last_cat_id = category_id
                else:
                    last_cat_id = category_id
                    continue


        # == EXTRACT all capsed links – they are brands ==#
        brands_list = hxs.select("//ul[@class='sitemap']/li[not(@class='level-1')]/a/text()").extract()
        brands = list(set([brand for brand in brands_list if brand.isupper() and not [ch for ch in brand if ch.isdigit()]]))

        for name, links in first_lvl_cats.iteritems():
            for link in links:
                yield Request(url=link, meta={'category': name, 'brands': brands}, callback=self.parse_category)


    def parse_category(self, response):

        hxs = HtmlXPathSelector(response=response)
        brands = response.meta['brands']
        category = response.meta['category']
        items = hxs.select("//div[@class='listing-type-grid catalog-listing']//li[@class='item']/p[@class='product-image']/a/@href").extract()

        for item in items:
            yield Request(item, meta={'category': category, 'brands': brands}, callback=self.parse_item)


        # == Look for the 'next page' button ==#
        try:
            next_page = hxs.select("//td[@class='pages']//a/img[contains(@src, 'arrow_right)]/parent::a/@href").extract()[0]
            yield Request(next_page, meta={'category': category, 'brands': brands}, callback=self.parse_category)
        except:
            pass



    def parse_item(self, response):

        hxs = HtmlXPathSelector(response)
        l = ProductLoader(item=Product(), response=response)

        brands = response.meta['brands']
        name = hxs.select("//h1[@itemprop='name']/text()").extract()[0].title()

        try:
            price = hxs.select("//div[@class='product-shop']//span[contains(@id,'product-price')]/span/text()").extract()[0][:-2].replace(',', '.')
        except:
            price = hxs.select("//div[@class='product-shop']//span[contains(@id,'product-price')]/text()").extract()[0][:-2].replace(',', '.')

        price = ''.join(price.split()).replace(' ', '')
        stock = 1 if 'en stock' in hxs.select("//p[@class='availability']/text()").extract()[0] else 0

        brand = ''
        for brand in brands:
            if brand.lower() in name.lower():
                brand = brand
                break

        category = response.meta['category']

        try:
            image_url = hxs.select("//p[@class='product-image-zoom']/img/@src").extract()[0]
        except:
            image_url = ''

        try:
            sku = hxs.select("//div[@class='std']").extract()[0]
            sku = re.findall(re.compile('R.+f : ([\d*\s*]*)'), sku)[0].strip()
        except:
            sku = ''

        identifier = hxs.select("//input[@name='product']/@value").extract()[0]

        l.add_value('name', name)
        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('price', price)
        l.add_value('stock', stock)
        l.add_value('category', category)
        l.add_value('brand', brand)
        l.add_value('identifier', identifier)
        l.add_value('sku', sku)

        yield l.load_item()
