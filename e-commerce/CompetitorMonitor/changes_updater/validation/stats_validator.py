from decimal import Decimal
from collections import defaultdict
from . import ValidationError


def _get_percentage(total, x):
    total = Decimal(total)
    x = Decimal(x)
    if not total:
        return None
    else:
        return (x * 100) / total


class ChangesValidator(object):
    def __init__(self, settings=None):
        self.settings = settings or {}

    def validate(self, stats):
        products = stats['products']
        previous_products = stats['previous_products']
        new_products = stats['new_products']
        old_products = stats['old_products']
        price_changes = stats['price_changes']
        matched_deletions = stats['matched_deletions']
        matched = stats['matched']

        if not products:
            yield ValidationError(24, 'The crawl has finished with 0 products collected')

        if previous_products and products:
            max_additions = self.settings['max_additions']
            if max_additions:
                max_additions = Decimal(max_additions)

            if max_additions and _get_percentage(previous_products, new_products) > max_additions:
                yield ValidationError(1, 'The crawl contains too many additions')

            max_deletions = self.settings['max_deletions']
            if max_deletions:
                max_deletions = Decimal(max_deletions)

            if max_deletions and _get_percentage(previous_products, old_products) > max_deletions:
                yield ValidationError(2, 'The crawl contains too many deletions')

            max_updates = self.settings['max_updates']
            if max_updates:
                max_updates = Decimal(max_updates)

            if max_updates and _get_percentage(previous_products, price_changes) > max_updates:
                yield ValidationError(23, 'The crawl contains too many updates')

            max_matched_deletions = self.settings['max_matched_deletions']
            if max_matched_deletions:
                max_matched_deletions = Decimal(max_matched_deletions)

            if matched and max_matched_deletions and _get_percentage(matched,
                                                                     matched_deletions) > max_matched_deletions:
                yield ValidationError(22, 'The crawl contains too many matched deletions')


class AdditionalChangesValidator(object):
    def __init__(self, settings=None):
        self.settings = settings or {}

    def validate(self, stats):
        previous_products = stats['previous_products']
        if not previous_products:
            return

        additional_empty = stats['additional_empty']
        max_additional_to_empty = self.settings['max_additional_to_empty']
        if max_additional_to_empty:
            max_additional_to_empty = Decimal(max_additional_to_empty)

        if max_additional_to_empty and \
                        _get_percentage(previous_products, additional_empty) > max_additional_to_empty:
            yield ValidationError(11, 'The crawl contains too many additional changes to an empty value')

        additional_changes_image_url = stats['additional_changes_image_url']
        max_image_url_changes = self.settings['max_image_url_changes']
        if max_image_url_changes:
            max_image_url_changes = Decimal(max_image_url_changes)
        if max_image_url_changes and _get_percentage(previous_products,
                                                     additional_changes_image_url) > max_image_url_changes:
            yield ValidationError(12, 'The crawl contains too many image url changes')

        additional_changes_sku = stats['additional_changes_sku']
        max_sku_changes = self.settings['max_sku_changes']
        if max_sku_changes:
            max_sku_changes = Decimal(max_sku_changes)
        if max_sku_changes and _get_percentage(previous_products,
                                               additional_changes_sku) > max_sku_changes:
            yield ValidationError(9, 'The crawl contains too many SKU value changes')

        additional_changes_category = stats['additional_changes_category']
        max_category_changes = self.settings['max_category_changes']
        if max_category_changes:
            max_category_changes = Decimal(max_category_changes)
        if max_category_changes and _get_percentage(previous_products,
                                                    additional_changes_category) > max_category_changes:
            yield ValidationError(13, 'The crawl contains too many category changes')

        out_stock = stats['out_stock']
        max_out_stock = self.settings['max_out_stock']
        if max_out_stock:
            max_out_stock = Decimal(max_out_stock)
        if max_out_stock and _get_percentage(previous_products, out_stock) > max_out_stock:
            yield ValidationError(15, 'The crawl contains too many products moved from In Stock to Out of Stock')


class MetadataChangesValidator(object):
    def __init__(self, settings=None):
        self.settings = settings or {}

    def validate(self, stats):
        if self.settings.get('collect_reviews') and not stats['reviews']:
            yield ValidationError(17, 'No reviews. Spider should collect reviews,'
                                      ' but no reviews were collected on this crawl')
