from product_spiders.spiders.arco_a.amazon_co_uk import ArcoAmazonCoUkSpider


class ArcoBAmazonCoUkSpider(ArcoAmazonCoUkSpider):
    name = 'arco-b-new-amazon.co.uk'

    website_id = 272

    member_id = 32

    category = 'B'

    full_crawl_day = 1