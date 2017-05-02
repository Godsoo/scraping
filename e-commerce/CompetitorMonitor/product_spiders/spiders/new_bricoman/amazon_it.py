from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider


class AmazonItSpider(BaseAmazonSpider):
    name = 'newbricoman-amazon.it'
    allowed_domains = ['amazon.it']
    domain = 'www.amazon.it'

    user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'

    type = 'category'
    _use_amazon_identifier = True
    only_buybox = True
    collect_products_with_no_dealer = True
    do_retry = True
    max_retry_count = 5
    _max_pages = 200

    try_suggested = False

    def get_category_url_generator(self):
        urls = [
            {
                'url': u'http://www.amazon.it/s/ref=nb_sb_noss?__mk_it_IT=%C3%85M%C3%85%C5%BD%C3%95%C3%91&url=node%3D679995031&field-keywords=',
                'category': 'Elettrodomestici per la casa'},
            {
                'url': u'http://www.amazon.it/s/ref=nb_sb_noss?__mk_it_IT=%C3%85M%C3%85%C5%BD%C3%95%C3%91&url=node%3D731505031&field-keywords=',
                'category': 'Utensili manuali'},
            {
                'url': u'http://www.amazon.it/s/ref=nb_sb_noss?__mk_it_IT=%C3%85M%C3%85%C5%BD%C3%95%C3%91&url=node%3D731505031&field-keywords=',
                'category': 'Utensili elettrici'},
            {
                'url': u'http://www.amazon.it/s/ref=nb_sb_noss?__mk_it_IT=%C3%85M%C3%85%C5%BD%C3%95%C3%91&url=search-alias%3Dlighting&field-keywords=',
                'category': 'Illuminazione'},
            {
                'url': u'http://www.amazon.it/s/ref=nb_sb_noss?__mk_it_IT=%C3%85M%C3%85%C5%BD%C3%95%C3%91&url=search-alias%3Ddiy&field-keywords=',
                'category': 'Fai da te'},
            {
                'url': u'http://www.amazon.it/s/ref=nb_sb_noss?__mk_it_IT=%C3%85M%C3%85%C5%BD%C3%95%C3%91&url=node%3D473568031&field-keywords=&rh=n%3A473568031',
                'category': 'Pile e caricabatterie'},
            {
                'url': u'http://www.amazon.it/s/ref=sr_in_g_p_89_73?rh=n%3A425916031%2Cp_89%3AGewiss&bbn=425916031&ie=UTF8&qid=1386942623&rnid=1688663031',
                'category': 'Informatica'}
        ]

        for url in urls:
            yield (url['url'], url['category'])
