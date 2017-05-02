import os
from product_spiders.spiders.arco_a.slingsby_spider import SlingsbySpider


class SlingsbySpider_B(SlingsbySpider):
    name = 'arco-b-slingsby.com'

    website_id = 367
    all_products_file = os.path.join(SlingsbySpider.root_path, SlingsbySpider.name + '_products.csv')
    do_full_run = False
