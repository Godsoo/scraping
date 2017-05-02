# -*- coding: utf-8 -*-
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider


class AmazonSpiderDirect(BaseAmazonSpider):
    name = 'newbricoman-amazon.it-direct'
    domain = 'www.amazon.it'

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:24.0) Gecko/20100101 Firefox/24.0'

    type = 'category'
    _use_amazon_identifier = True
    amazon_direct = True
    sellers = ['Amazon']
    exclude_sellers = []
    collect_products_with_no_dealer = False
    do_retry = True
    max_retry_count = 5
    _max_pages = 200

    try_suggested = False

    def get_category_url_generator(self):
        urls = [
            ('http://www.amazon.it/s/ref=nb_sb_noss?url=node%3D679995031&field-keywords=&emi=A11IL2PNWYJU7H', 'Elettrodomestici per la casa'),
            ('http://www.amazon.it/s/ref=nb_sb_noss?url=node%3D731504031&field-keywords=&emi=A11IL2PNWYJU7H', 'Utensili manuali'),
            ('http://www.amazon.it/s/ref=nb_sb_noss?url=node%3D731505031&field-keywords=&emi=A11IL2PNWYJU7H', 'Utensili elettrici'),
            ('http://www.amazon.it/s/ref=nb_sb_noss?url=search-alias%3Dlighting&field-keywords=&emi=A11IL2PNWYJU7H', 'Illuminazione'),
            ('http://www.amazon.it/s/ref=nb_sb_noss?url=search-alias%3Ddiy&field-keywords=&emi=A11IL2PNWYJU7H', 'Fai da te'),
            ('http://www.amazon.it/s/ref=sr_nr_n_8?rh=n%3A412609031%2Cn%3A!412610031%2Cn%3A1463299031%2Cn%3A473568031&bbn=1463299031&ie=UTF8&qid=1380741858&rnid=1463299031&emi=A11IL2PNWYJU7H', 'Pile e caricabatterie'),
            ('http://www.amazon.it/s/ref=sr_in_g_p_89_73?rh=n%3A425916031%2Cp_89%3AGewiss&bbn=425916031&ie=UTF8&qid=1386942623&rnid=1688663031&emi=A11IL2PNWYJU7H', 'Informatica'),
        ]

        for url, name in urls:
            yield (url, name)
