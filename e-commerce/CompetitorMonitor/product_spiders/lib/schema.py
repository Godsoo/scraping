from extruct.w3cmicrodata import MicrodataExtractor


class SpiderSchema(object):

    def __init__(self, response):
        mde = MicrodataExtractor()
        try:
            self.data = mde.extract(response.body, response.url)
        except:
            self.data = mde.extract(response.body.decode('latin-1'), response.url)

    def get_products(self):
        if self.data and 'items' in self.data:
            products = filter(lambda a: a['type'] == 'http://schema.org/Product', self.data['items'])
            return [p['properties'] for p in products]
        return []

    def get_product(self):
        products = self.get_products()
        if products:
            return products[0]
        return {}
    
    def get_category(self):
        if self.data and 'items' in self.data:
            breadcrumblist = filter(lambda a: a['type'] == 'http://schema.org/BreadcrumbList', self.data['items'])
            if breadcrumblist and breadcrumblist[0].get('properties'):
                return [b['properties']['name'] for b in breadcrumblist[0]['properties']['itemListElement']]
        return []
