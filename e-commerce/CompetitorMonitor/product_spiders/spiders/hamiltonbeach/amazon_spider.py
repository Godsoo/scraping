from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider


class HamiltonBeachAmazonSpider(BaseAmazonSpider):
    """
    WARNING!!!
    The spider does not collect prices for product (all have None).
    This was done intentionally because client does not pay for it.
    If you want to make it collect prices - remove `transform_price` method,
    or remade it for your needs
    """
    name = 'hamiltonbeach-amazon.com'
    domain = 'amazon.com'
    type = 'category'
    only_buybox = True
    model_as_sku = True
    do_retry = True
    collect_products_with_no_dealer = True
    collect_reviews = True
    parse_options = True
    reviews_once_per_product_without_dealer = True

    def get_category_url_generator(self):
        urls = [
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D7956268011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Soda Makers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289925&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Contact Grills']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289742&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances',
                          u'Coffee, Tea & Espresso Appliances']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289918&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Deep Fryers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D13838451&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Countertop Burners']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289914&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Blenders']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289917&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Bread Machines']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D8614937011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Cake Pop & Mini Cake Makers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D13838491&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Electric Woks']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3117954011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Electric Pressure Cookers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289920&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Food Processors']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3117951011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Hot Pots']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D13838461&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Electric Griddles']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D13838481&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Electric Skillets']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289924&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Ice Cream Machines']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289929&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Mixers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289926&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Juicers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289933&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Ovens & Toasters']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D678540011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Rice Cookers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289940&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Slow Cookers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D678541011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Steamers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289942&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Waffle Irons']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289867&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Cutlery & Knife Accessories', u'Knife Sharpeners']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D1090752&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Dehydrators']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3741661&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Bagel Slicers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D297927011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Chocolate Fountains']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3741671&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Crepe Makers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3117953011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Electric Wine Bottle Openers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D1090760&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Food Grinders & Mills']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D1090754&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Egg Cookers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D1090758&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Electric Slicers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D1090762&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Pizzelle Makers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D1090764&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Popcorn Poppers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D1090766&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Sandwich Makers & Panini Presses']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D1090768&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Vacuum Sealers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3741681&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Quesadilla & Tortilla Makers']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3117959011&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Shaved Ice Machines']},
            {'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D16012141&field-keywords=',
             'category': [u'Home & Kitchen', u'Kitchen & Dining', u'Small Appliances', u'Specialty Appliances',
                          u'Yogurt Makers']}
        ]
        for url in urls:
            yield (url['url'], url['category'])

        urls2 = [
            {'category': ['Home & Kitchen',
                          'Heating, Cooling & Air Quality',
                          'Air Purifiers'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D267554011&field-keywords='},
            {'category': ['Home & Kitchen', 'Kitchen & Dining', 'Cookware', 'Skillets'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289829&field-keywords='},
            {'category': ['Home & Kitchen',
                          'Kitchen & Dining',
                          'Small Appliances',
                          'Countertop Burners'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D13838451&field-keywords='},
            {'category': ['Home & Kitchen',
                          'Kitchen & Dining',
                          'Kitchen Utensils & Gadgets',
                          'Can Openers'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289755&field-keywords='},
            {'category': ['Home & Kitchen',
                          'Kitchen & Dining',
                          'Dining & Entertaining',
                          'Serveware',
                          'Beverage Serveware',
                          'Teapots & Coffee Servers',
                          'Coffee Urns'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D367224011&field-keywords='},
            {'category': ['Home & Kitchen', 'Kitchen & Dining', 'Cookware', 'Fondue'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289820&field-keywords='},
            {'category': ['Home & Kitchen',
                          'Kitchen & Dining',
                          'Kitchen Utensils & Gadgets',
                          'Seasoning & Spice Tools',
                          'Choppers & Mincers',
                          'Choppers'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D678514011&field-keywords='},
            {'category': ['Home and Kitchen',
                          'Irons & Steamers',
                          'Irons'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D510242&field-keywords='},
            {'category': ['Home and Kitchen',
                          'Irons & Steamers',
                          'Garment Streamers'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D510248&field-keywords='},
            {'category': ['Patio, Lawn & Garden',
                          'Grills & Outdoor Cooking',
                          'Grills',
                          'Freestanding Grills'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3480667011&field-keywords='},
            {'category': ['Appliances', 'Ice Makers'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D2399939011&field-keywords='},
            {'category': ['Home & Kitchen',
                          'Kitchen & Dining',
                          'Cutlery & Knife Accessories',
                          'Electric Knives'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D3737391&field-keywords='},
            {'category': ['Home & Kitchen',
                          'Kitchen & Dining',
                          'Small Appliances',
                          'Microwave Ovens'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D289935&field-keywords='},
            {'category': ['Home & Kitchen',
                          'Kitchen & Dining',
                          'Bakeware',
                          'Candy Making Supplies'],
            'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D2231404011&field-keywords='},
            {'category': ['Home & Kitchen',
                          'Heating, Cooling & Air Quality',
                          'Household Fans',
                          'Tower Fans'],
             'url': 'http://www.amazon.com/s/ref=nb_sb_noss?url=node%3D241127011&field-keywords='}
        ]
        for url in urls2:
            yield (url['url'], url['category'])

    def match(self, meta, search_item, found_item):
        return True

    def transform_price(self, price):
        return 0
