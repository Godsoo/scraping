# -*- coding: utf-8 -*-
from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider


class AmazonSpider(BaseAmazonSpider):
    name = 'axemusic-amazon.ca-music'
    domain = 'amazon.ca'

    type = 'category'

    all_sellers = False
    only_buybox = True
    _use_amazon_identifier = True
    collect_products_from_list = True
    collected_identifiers = set()

    try_suggested = False
    do_retry = True
    rotate_agent = True

    def get_category_url_generator(self):
        urls = [
            {'url': 'http://www.amazon.ca/s/ref=nb_sb_noss?url=node%3D8396329011&field-keywords=',
             'category': 'Bass Guitars'},
            {'url': 'http://www.amazon.ca/s/ref=nb_sb_noss?url=node%3D8396311011&field-keywords=',
             'category': 'Guitars'},
            {'url': 'http://www.amazon.ca/s/ref=nb_sb_noss?url=node%3D8396471011&field-keywords=',
             'category': 'Drums & Percussion'},
            {'url': 'http://www.amazon.ca/s/ref=nb_sb_noss?url=node%3D8396702011&field-keywords=',
             'category': 'Keyboards'},
            {'url': 'http://www.amazon.ca/s/ref=nb_sb_noss?url=node%3D8397410011&field-keywords=',
             'category': 'DJ, Electronic Music & Karaoke'},
            {'url': 'http://www.amazon.ca/s/ref=nb_sb_noss?url=node%3D8397067011&field-keywords=',
             'category': 'Amplifiers, Parts & Accessories'},
            {'url': 'http://www.amazon.ca/s/ref=nb_sb_noss?url=node%3D8397113011&field-keywords=',
             'category': 'Stage & Studio'}
        ]

        for row in urls:
            yield (row['url'], row['category'])
