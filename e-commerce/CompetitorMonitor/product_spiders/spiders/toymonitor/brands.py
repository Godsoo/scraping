import re
import os

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT = os.path.join(HERE, 'brands.csv')

class BrandSelector(object):
    def __init__(self, errors, path=DEFAULT):
        self.brands = {}
        self.errors = errors
        self.seen_brands = set()
        with open(path) as f:
            for line in f:
                normalized = self.normalize_brand(line)
                if normalized not in self.brands:
                    self.brands[normalized] = line.strip()  

    def normalize_brand(self, brand):
        normalized = brand or ''
        normalized = normalized.strip().lower()
        normalized = ''.join(re.findall("([A-Za-z0-9])", normalized))
        return normalized

    def get_brand(self, brand):
        try:
            normalized = self.normalize_brand(brand)
            real_brand = self.brands.get(normalized)
            if not real_brand:
                if brand not in self.seen_brands:
                    self.seen_brands.add(brand)
                    self.errors.append('New brand found (Update manufacturer file): {}'.format(brand))
                return brand
            else:
                return real_brand
        except Exception:
            return brand
