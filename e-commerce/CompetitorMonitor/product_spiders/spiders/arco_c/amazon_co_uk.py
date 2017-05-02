from product_spiders.spiders.arco_a.amazon_co_uk import ArcoAmazonCoUkSpider


class ArcoCAmazonCoUkSpider(ArcoAmazonCoUkSpider):
    name = 'arco-c-amazon.co.uk'

    category = 'C'

    website_id = 273
    member_id = 33

    full_crawl_day = 6
