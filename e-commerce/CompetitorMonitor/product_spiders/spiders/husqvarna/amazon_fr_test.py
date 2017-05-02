# -*- coding: utf-8 -*-
__author__ = 'juraseg'
import os

from scrapy.selector import HtmlXPathSelector

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper

HERE = os.path.abspath(os.path.dirname(__file__))


class HusqvarnaAmazonScraper(AmazonScraper):
    def scrape_product_details_page(self, response, only_color=False):
        res = super(HusqvarnaAmazonScraper, self).scrape_product_details_page(response, only_color)

        hxs = HtmlXPathSelector(response)

        sku = hxs.select(u'//div[@class="pdTab"]/table//tr[td[contains(text(), "Référence")]]/td[@class="value"]/text()').extract()
        if sku:
            res['sku'] = sku[0]

        return res


class HusqvarnaAmazonSpider(BaseAmazonSpider):
    name = 'husqvarna-amazon.fr_test'
    domain = 'amazon.fr'

    type = 'category'
    all_sellers = True

    _use_amazon_identifier = True

    collect_products_from_list = False

    do_retry = True

    collect_reviews = True
    reviews_once_per_product_without_dealer = True

    scraper_class = HusqvarnaAmazonScraper

    def proxy_service_check_response(self, response):
        return self.scraper.antibot_protection_raised(response.body_as_unicode())

    def get_category_url_generator(self):
        urls = [
            # subcategories
            # first cat
            u'http://www.amazon.fr/McCulloch-Bricolage/s?ie=UTF8&page=1&rh=i%3Adiy%2Ck%3AMcCulloch%2Cp_89%3AMcCulloch',
            u'http://www.amazon.fr/McCulloch-Jardin/s?ie=UTF8&page=1&rh=i%3Agarden%2Ck%3AMcCulloch%2Cp_89%3AMcCulloch',
            u'http://www.amazon.fr/McCulloch-Cuisine-Maison/s?ie=UTF8&page=1&rh=i%3Akitchen%2Ck%3AMcCulloch%2Cp_89%3AMcCulloch',
            u'http://www.amazon.fr/McCulloch-V%C3%AAtements-accessoires/s?ie=UTF8&page=1&rh=i%3Aclothing%2Ck%3AMcCulloch%2Cp_89%3AMcCulloch',
            u'http://www.amazon.fr/McCulloch-Sports-Loisirs/s?ie=UTF8&page=1&rh=i%3Asports%2Ck%3AMcCulloch%2Cp_89%3AMcCulloch',
            u'http://www.amazon.fr/McCulloch-Animalerie/s?ie=UTF8&page=1&rh=i%3Apets%2Ck%3AMcCulloch%2Cp_89%3AMcCulloch',
            u'http://www.amazon.fr/McCulloch-Auto-Moto/s?ie=UTF8&page=1&rh=i%3Aautomotive%2Ck%3AMcCulloch%2Cp_89%3AMcCulloch',

            # second cat
            u'http://www.amazon.fr/Flymo-Bricolage/s?ie=UTF8&page=1&rh=i%3Adiy%2Ck%3AFlymo%2Cp_89%3AFlymo',
            u'http://www.amazon.fr/Flymo-Jardin/s?ie=UTF8&page=1&rh=i%3Agarden%2Ck%3AFlymo%2Cp_89%3AFlymo',
            u'http://www.amazon.fr/Flymo-Cuisine-Maison/s?ie=UTF8&page=1&rh=i%3Akitchen%2Ck%3AFlymo%2Cp_89%3AFlymo',
            u'http://www.amazon.fr/Flymo-Sant%C3%A9-Soins-corps/s?ie=UTF8&page=1&rh=i%3Ahpc%2Ck%3AFlymo%2Cp_89%3AFlymo',
            u'http://www.amazon.fr/Flymo-Beaut%C3%A9-Parfum/s?ie=UTF8&page=1&rh=i%3Abeauty%2Ck%3AFlymo%2Cp_89%3AFlymo',
            u'http://www.amazon.fr/Flymo-Luminaires-Eclairage/s?ie=UTF8&page=1&rh=i%3Alighting%2Ck%3AFlymo%2Cp_89%3AFlymo',
            u'http://www.amazon.fr/Flymo-High-Tech/s?ie=UTF8&page=1&rh=i%3Aelectronics%2Ck%3AFlymo%2Cp_89%3AFlymo',
            u'http://www.amazon.fr/Flymo-V%C3%AAtements-accessoires/s?ie=UTF8&page=1&rh=i%3Aclothing%2Ck%3AFlymo%2Cp_89%3AFlymo',

            # third cat
            u'http://www.amazon.fr/Gardena-Bricolage/s?ie=UTF8&page=1&rh=i%3Adiy%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Jardin/s?ie=UTF8&page=1&rh=i%3Agarden%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Cuisine-Maison/s?ie=UTF8&page=1&rh=i%3Akitchen%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Auto-Moto/s?ie=UTF8&page=1&rh=i%3Aautomotive%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Sports-Loisirs/s?ie=UTF8&page=1&rh=i%3Asports%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Fournitures-de-bureau/s?ie=UTF8&page=1&rh=i%3Aoffice-products%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Sant%C3%A9-Soins-corps/s?ie=UTF8&page=1&rh=i%3Ahpc%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-V%C3%AAtements-accessoires/s?ie=UTF8&page=1&rh=i%3Aclothing%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Jeux-Jouets/s?ie=UTF8&page=1&rh=i%3Atoys%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-High-Tech/s?ie=UTF8&page=1&rh=i%3Aelectronics%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Luminaires-Eclairage/s?ie=UTF8&page=1&rh=i%3Alighting%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Bagages/s?ie=UTF8&page=1&rh=i%3Aluggage%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Gros-%C3%A9lectrom%C3%A9nager/s?ie=UTF8&page=1&rh=i%3Aappliances%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-B%C3%A9b%C3%A9s-Pu%C3%A9riculture/s?ie=UTF8&page=1&rh=i%3Ababy%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Animalerie/s?ie=UTF8&page=1&rh=i%3Apets%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Instruments-de-musique-Sono/s?ie=UTF8&page=1&rh=i%3Ami%2Ck%3AGardena%2Cp_89%3AGardena',
            u'http://www.amazon.fr/Gardena-Beaut%C3%A9-Parfum/s?ie=UTF8&page=1&rh=i%3Abeauty%2Ck%3AGardena%2Cp_89%3AGardena',

            # big cats
            'http://www.amazon.fr/s/ref=sr_nr_p_89_0?rh=i%3Aaps%2Ck%3AMcCulloch%2Cp_89%3AMcCulloch&keywords=McCulloch&ie=UTF8&qid=1403216320&rnid=1680780031',
            'http://www.amazon.fr/s/ref=sr_nr_p_89_0?rh=i%3Aaps%2Ck%3AFlymo%2Cp_89%3AFlymo&keywords=Flymo&ie=UTF8&qid=1403269337&rnid=1680780031',
            'http://www.amazon.fr/s/ref=sr_nr_p_89_0?rh=i%3Aaps%2Ck%3AGardena%2Cp_89%3AGardena&keywords=Gardena&ie=UTF8&qid=1403269377&rnid=1680780031',
        ]
        for url in urls:
            yield (url, '')
