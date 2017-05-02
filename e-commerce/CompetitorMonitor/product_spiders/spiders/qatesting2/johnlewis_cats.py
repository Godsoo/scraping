from product_spiders.base_spiders.john_lewis import JohnLewisBaseSpider


class JohnLewisSpider(JohnLewisBaseSpider):
    name = 'qatesting2-johnlewis-base-test'
    categories = [('Cooking & Dining', ''), ('Room', 'Utility room'), ('Room', 'Kitchen'),
                  ('Home Appliances', 'Cookers & Ovens'), ('Small Appliances', ''),
                  ('Gift Food', ''), ('Alcohol Gifts', '')]
