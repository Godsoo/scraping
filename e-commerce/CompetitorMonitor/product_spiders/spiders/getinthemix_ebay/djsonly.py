from basespider import BaseGetInTheMixEBaySpider


class DJsOnlySpider(BaseGetInTheMixEBaySpider):
    name = 'getinthemix-ebay-djsonly'
    start_urls = ('http://stores.ebay.co.uk/DJs-Only-Store',)

    def get_promotion_text(self, hxs):
        promotion = hxs.select('//h2[@id="subTitle"]/text()').extract()
        return ''.join(promotion).strip()
