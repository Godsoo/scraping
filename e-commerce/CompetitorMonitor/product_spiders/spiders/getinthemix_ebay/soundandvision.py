from basespider import BaseGetInTheMixEBaySpider


class SoundAndVisionSpider(BaseGetInTheMixEBaySpider):
    name = 'getinthemix-ebay-soundandvision'
    start_urls = ('http://stores.ebay.co.uk/SOUND-AND-VISION-EXPRESS',)
