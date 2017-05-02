import re


def brand_in_file(brand_name, brands_to_monitor):
    clean_name = re.sub(r'\W+', '', brand_name.upper())
    if clean_name in brands_to_monitor or clean_name.split(' ')[0].upper() in brands_to_monitor:
        return True
    for brand in brands_to_monitor:
        file_brand = re.sub(r'\W+', '', brand.upper())
        if file_brand in clean_name:
            return True
    return False
