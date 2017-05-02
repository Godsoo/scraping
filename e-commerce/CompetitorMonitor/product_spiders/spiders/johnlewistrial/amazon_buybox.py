# -*- coding: utf-8 -*-
from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider


class AmazonSpider(BaseAmazonSpider):
    name = 'johnlewistrial-amazon.co.uk-buybox'
    domain = 'amazon.co.uk'

    type = 'category'

    only_buybox = True
    collect_new_products = True
    collect_used_products = False
    _use_amazon_identifier = True
    collected_identifiers = set()
    collect_products_from_list = True

    collect_reviews = True
    #review_date_format = u'%d %b. %Y'
    review_date_format = None

    try_suggested = False
    do_retry = True

    rotate_agent = True

    def get_category_url_generator(self):
        urls = [
            {'category': 'Large appliances > Hoods',
             'url': 'http://www.amazon.co.uk/s/ref=lp_1345796031_nr_n_12?fst=as%3Aoff&rh=n%3A11052681%2Cn%3A%213147411%2Cn%3A391784011%2Cn%3A1345796031%2Cn%3A1391011031&bbn=1345796031&ie=UTF8&qid=1426156882&rnid=1345796031'},
            {'category': 'Large appliances > Washing machines & tumble driers > Washing machines',
             'url': 'http://www.amazon.co.uk/s/ref=sr_nr_n_4?fst=as%3Aoff&rh=n%3A908798031%2Cn%3A%21908799031%2Cn%3A11712521%2Cn%3A3618681&bbn=11712521&ie=UTF8&qid=1426156118&rnid=11712521'},
            {'category': 'Large appliances > Cooktops',
             'url': 'http://www.amazon.co.uk/s/ref=sr_nr_n_0?fst=as%3Aoff&rh=n%3A11052681%2Cn%3A1391010031%2Ck%3Ahobs&keywords=hobs&ie=UTF8&qid=1426157908&rnid=3147411'},
            {'category': 'Vacuuming, cleaning & ironing > Irons, steamers & accessories > Irons',
             'url': 'http://www.amazon.co.uk/Steam-Irons/b/ref=amb_link_186356847_37?ie=UTF8&node=10706461&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Small kitchen appliances > Toasters',
             'url': 'http://www.amazon.co.uk/Toaster/b/ref=amb_link_186356847_18?ie=UTF8&node=11716951&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Large appliances > Cookers & ovens > Cooker ovens',
             'url': 'http://www.amazon.co.uk/s/ref=sr_nr_n_0?fst=as%3Aoff&rh=n%3A908798031%2Cn%3A%211178868031%2Cn%3A%211178869031%2Cn%3A10706541%2Cn%3A1391012031&bbn=10706541&ie=UTF8&qid=1426156463&rnid=10706541'},
            {'category': 'Large appliances > Fridges & freezers > Fridges',
             'url': 'http://www.amazon.co.uk/s/ref=sr_nr_n_4?fst=as%3Aoff&rh=n%3A908798031%2Cn%3A%211178868031%2Cn%3A%211178869031%2Cn%3A10706331%2Cn%3A10706341&bbn=10706331&ie=UTF8&qid=1426156120&rnid=10706331'},
            {'category': 'Large appliances > Ovens',
             'url': 'http://www.amazon.co.uk/s/ref=nb_sb_noss?url=node%3D1391012031&field-keywords=&rh=n%3A908798031%2Cn%3A1391012031'},
            {'category': 'Large appliances > Dishwashers',
             'url': 'http://www.amazon.co.uk/Dishwashers-Kitchen-Appliances-Home-Garden/b/ref=amb_link_186356847_41?ie=UTF8&node=10706491&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Large appliances > Washing machines & tumble dryers > Dryers',
             'url': 'http://www.amazon.co.uk/s/ref=sr_nr_n_0?fst=as%3Aoff&rh=n%3A908798031%2Cn%3A%21908799031%2Cn%3A11712521%2Cn%3A1391019031&bbn=11712521&ie=UTF8&qid=1426156118&rnid=11712521'},
            {'category': 'Large appliances > Fridges & freezers > Freezers',
             'url': 'http://www.amazon.co.uk/s/ref=sr_nr_n_2?fst=as%3Aoff&rh=n%3A908798031%2Cn%3A%211178868031%2Cn%3A%211178869031%2Cn%3A10706331%2Cn%3A10706351&bbn=10706331&ie=UTF8&qid=1426156120&rnid=10706331'},
            {'category': 'Large appliances > Fridges & freezers > Fridge-freezers',
             'url': 'http://www.amazon.co.uk/s/ref=sr_nr_n_3?fst=as%3Aoff&rh=n%3A908798031%2Cn%3A%211178868031%2Cn%3A%211178869031%2Cn%3A10706331%2Cn%3A10706361&bbn=10706331&ie=UTF8&qid=1426155763&rnid=10706331'},
            {'category': 'Large appliances > Washing machines & tumble dryers > Washer-dryers',
             'url': 'http://www.amazon.co.uk/s/ref=sr_nr_n_3?fst=as%3Aoff&rh=n%3A908798031%2Cn%3A%21908799031%2Cn%3A11712521%2Cn%3A11712551&bbn=11712521&ie=UTF8&qid=1426156118&rnid=11712521'},
            {'category': 'Small kitchen appliances > Coffee machines',
             'url': 'http://www.amazon.co.uk/Coffee-Machines/b/ref=amb_link_186356847_7?ie=UTF8&node=516075031&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Small kitchen appliances > Fryers',
             'url': 'http://www.amazon.co.uk/Deep-Fat-Fryers/b/ref=amb_link_186356847_8?ie=UTF8&node=3147531&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Small Kitchen Appliances > Microwaves',
             'url': 'http://www.amazon.co.uk/Cookers-Ovens-Kitchen-Appliances-Home/s/ref=sr_nr_n_3?fst=as%3Aoff&rh=n%3A908798031%2Cn%3A%211178868031%2Cn%3A%211178869031%2Cn%3A10706541%2Cn%3A11716911&bbn=10706541&ie=UTF8&qid=1426155912&rnid=10706541&ajr=2'},
            {'category': 'Small kitchen appliances > Sandwich toasters & panini presses',
             'url': 'http://www.amazon.co.uk/Sandwich-Toasters-Panini-Presses/b/ref=amb_link_186356847_15?ie=UTF8&node=3147611&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Small kitchen appliances > Slow cookers',
             'url': 'http://www.amazon.co.uk/Slow-Cookers-Kitchen-Appliances-Home/b/ref=amb_link_186356847_16?ie=UTF8&node=3147641&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Small kitchen appliances > Blenders, mixers & food processors > Food processors',
             'url': 'http://www.amazon.co.uk/Food-Processors-Kitchen-Appliances-Home/b/ref=amb_link_186356847_9?ie=UTF8&node=3147561&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Small kitchen appliances > Blenders, mixers & food processors > Blenders',
             'url': 'http://www.amazon.co.uk/Blenders-Kitchen-Appliances-Home-Garden/b/ref=amb_link_186356847_5?ie=UTF8&node=10706571&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1DZ2CKZY4AMB2J3CX6M7&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Small kitchen appliances > Kettles & hot water dispensers',
             'url': 'http://www.amazon.co.uk/Kettle/b/ref=amb_link_186356847_12?ie=UTF8&node=3538310031&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1WGWRJ43AF7YZT1ZJP35&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'},
            {'category': 'Vacuuming, cleaning & ironing > Vacuums & floor care > Vacuums',
             'url': 'http://www.amazon.co.uk/Vacuum-Cleaners/b/ref=amb_link_186356847_34?ie=UTF8&node=125698031&pf_rd_m=A3P5ROKL5A1OLE&pf_rd_s=merchandised-search-leftnav&pf_rd_r=1DZ2CKZY4AMB2J3CX6M7&pf_rd_t=101&pf_rd_p=588259707&pf_rd_i=391784011'}
        ]

        for row in urls:
            yield (row['url'], row['category'])
