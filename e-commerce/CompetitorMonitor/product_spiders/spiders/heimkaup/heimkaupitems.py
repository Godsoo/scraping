from scrapy.item import Item, Field
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from decimal import Decimal


from scrapy import log

class HeimkaupMeta(Item):
    cost_price = Field()
    net_price = Field()
    vid = Field()
     
class HeimkaupProduct(Product):
    def __setitem__(self, key, value):
        '''
          Adds price without tax 24% as metadata net_price
        '''
        super(HeimkaupProduct, self).__setitem__(key, value)
        if key == 'price':
            value = value if value else Decimal(0)
            super(HeimkaupProduct, self).__setitem__(key, value)

            net_price = str((Decimal(value)/Decimal('1.24')).quantize(Decimal('1.00')))
            try:
                metadata = super(HeimkaupProduct, self).__getitem__('metadata')
            except KeyError:
                metadata = HeimkaupMeta()
            metadata['net_price'] = net_price
            super(HeimkaupProduct, self).__setitem__('metadata', metadata)
