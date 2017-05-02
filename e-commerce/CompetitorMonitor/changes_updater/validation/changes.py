from . import Validator, ValidationError
from ..changes import Change
from decimal import Decimal


class PriceChangeValidator(Validator):
    accept_codes = [Change.UPDATE]
    code = 14
    msg = u'Invalid price change for {product} - old price: {old_price}, new price {price} ' \
          u'<a href="{url}" target="_blank">View Product</a>'

    def _change_perc(self, old_price, price):
        change = Decimal(0)

        if old_price != price:
            if not old_price:
                change = Decimal(100)
            else:
                change = Decimal((abs(price - old_price) * Decimal(100)) / old_price)

        return change

    def validate(self, result):
        max_percentage = self.settings['max_price_percentage_change']
        _, change_data = result.change_data()
        if max_percentage:
            max_percentage = Decimal(max_percentage)
            old_price = Decimal(change_data['old_price'] or 0)
            price = Decimal(change_data['price'] or 0)
            if old_price and (price or not self.settings['silent_updates'])\
                    and self._change_perc(old_price, price) > max_percentage:
                yield ValidationError(self.code, self.msg.format(product=change_data['identifier'],
                                                                 old_price=old_price, price=price,
                                                                 url=change_data['url']))