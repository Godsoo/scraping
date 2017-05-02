from basespider import BaseRosarioSpider


class TecnocalorFrascaSpider(BaseRosarioSpider):
    name = 'tecnocalorfrasca.ebay'
    start_urls = ('http://stores.ebay.it/Tecnocalor-Frasca/_i.html?_nkw=&submit=Cerca&_sid=169496197',)
