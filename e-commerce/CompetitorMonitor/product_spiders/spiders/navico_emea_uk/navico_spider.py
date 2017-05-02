from product_spiders.spiders.navico_emea.navico_spider import NavicoSpider_Emea as NavicoSpider

class NavicoSpider_EmeaUk(NavicoSpider):
    name = 'navico-emea-uk-navico.com'

    file_name = 'navico_products.csv'
