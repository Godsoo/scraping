"""

Name: ribblecycles-evanscycles.com
Account: Ribble Cycles

IMPORTANT!!

- Please be careful, this spider will be blocked if you're not
- This spider use EvansCyclesBaseSpider
- Do not use BSM here. EvansCyclesBaseSpider uses a custom BSM

"""

from product_spiders.base_spiders import EvansCyclesBaseSpider

class EvansCyclesComSpider(EvansCyclesBaseSpider):
    name = 'tweekscycles-evanscycles.com'

    # Copy data from products local file if exists
    secondary = True
