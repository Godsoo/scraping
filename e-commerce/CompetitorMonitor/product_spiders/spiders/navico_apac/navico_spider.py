from product_spiders.spiders.navico_emea.navico_spider import NavicoSpider_Emea as NavicoSpider

class NavicoSpider_Apac(NavicoSpider):
    name = 'navico-apac-navico.com'

    file_name = 'navico_products.csv'

