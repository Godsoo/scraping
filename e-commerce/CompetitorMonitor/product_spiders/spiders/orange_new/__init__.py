# -*- coding: utf-8 -*-
import os.path
import csv
import re
import logging
from decimal import Decimal

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.orange_new.items import OrangeNewMeta, OrangeNewMetaLoader
from product_spiders.utils import fix_spaces, remove_punctuation, remove_punctuation_and_spaces

ACCOUNT_NAME = 'Orange New'

HERE = os.path.abspath(os.path.dirname(__file__))


operator_names = [
    'Orange',
    'Swisscom',
    'M-Budget',
    'M-Budget Mobile',
    'MBudget',
    'MBudget Mobile',
    'Sunrise'
]

brand_synonyms = [
    ('lg', 'lg electronics')
]

class InvalidCategory(Exception):
    pass

class InvalidRecurringCharge(Exception):
    pass

class InvalidRecurringChargeForPricePlan(Exception):
    pass

def cache(fn):
    """
    >>> def test(x): return x
    >>> t = cache(test)
    >>> t('asd')
    'asd'
    >>> t(u'asd')
    'asd'
    >>> t(u'фыв') == u'фыв'
    True
    """
    cache = {}

    def new_fn(*args):
        key = "".join([unicode(x) for x in args])
        if not key in cache:
            cache[key] = fn(*args)
        return cache[key]
    return new_fn

@cache
def load_plan_category_mappings():
    categories = []
    with open(os.path.join(HERE, 'plan_category_mappings.csv')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            categories.append(row)

    return categories

@cache
def load_new_old_plan_mapping():
    mapping = []
    with open(os.path.join(HERE, 'new_to_old_priceplan_mapping.csv')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping.append(row)

    return mapping

@cache
def load_brands():
    brands = []
    with open(os.path.join(HERE, 'brands.csv')) as f:
        reader = csv.reader(f)
        for row in reader:
            brands.append(row[0])

    return brands

@cache
def load_categories():
    """
    >>> a = load_categories()
    >>> cats = {0: 'A', 16: 'CAT I', 41: 'CAT II', 56: 'CAT IIIb', 71: 'CAT III', 91: 'CAT IV', 111: 'CAT V'}
    >>> cats == a
    True
    """
    categories = {}
    with open(os.path.join(HERE, 'categories.csv')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            categories[Decimal(row['min_price'])] = row['category']
    return categories

@cache
def load_colors():
    """
    >>> colors = load_colors()
    >>> 'red' in colors
    True
    """
    colors = [x.decode('utf-8').strip() for x in open(os.path.join(HERE, 'colors.txt'))]
    return colors

@cache
def get_category_by_recurring_charge(recurring_charge):
    """
    >>> get_category_by_recurring_charge(0)
    'A'
    >>> get_category_by_recurring_charge(15)
    'A'
    >>> get_category_by_recurring_charge(16)
    'CAT I'
    >>> get_category_by_recurring_charge(45)
    'CAT II'
    >>> get_category_by_recurring_charge(60)
    'CAT IIIb'
    >>> get_category_by_recurring_charge('71')
    'CAT III'
    >>> get_category_by_recurring_charge(120)
    'CAT V'
    """
    try:
        recurring_charge = Decimal(recurring_charge)
    except ValueError:
        raise InvalidRecurringCharge("Error when converting recurring charge: %s" % recurring_charge)
    categories = load_categories()
    for min_price in sorted(categories.keys(), reverse=True):
        if recurring_charge >= min_price:
            return categories[min_price]
    raise InvalidRecurringCharge("Category not found for recurring charge: %s" % recurring_charge)

@cache
def get_priceplans_for_category(category, operator):
    plan_category_mapping = load_plan_category_mappings()
    plan_category_mapping = filter(lambda x: x['category'] == category, plan_category_mapping)
    if operator:
        plan_category_mapping = filter(lambda x: x['operator'] == operator, plan_category_mapping)

    return plan_category_mapping

@cache
def check_price_plan_exists(operator, plan_name, per_month):
    try:
        category = pick_plan_category2(operator, plan_name, per_month)
    except InvalidCategory:
        return False
    except InvalidRecurringChargeForPricePlan:
        return True

    return True

@cache
def load_branded_devices():
    branded_devices = []
    with open(os.path.join(HERE, 'branded_devices.csv')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            branded_devices.append(row)

    return branded_devices

@cache
def pick_plan_category2(operator, plan_name, per_month, ignore_rec_charge_diff=False):
    """
    >>> pick_plan_category2("M-Budget Mobile", "M-Budget Mobile Basic", Decimal('9.8'))
    ('A', Decimal('9.8'))
    >>> pick_plan_category2("M-Budget", "Basic", Decimal('9.8'))
    ('A', Decimal('9.8'))
    >>> pick_plan_category2("Orange", "Orange Young Star", Decimal('29'))
    ('CAT Y1', Decimal('29'))
    >>> pick_plan_category2("Orange", "Orange - Young Galaxy", Decimal('65'))
    ('CAT Y3', Decimal('65'))
    >>> pick_plan_category2("Swisscom", u"NATEL\u00ae xtra infinity S", Decimal('55'))
    ('CAT Y2', Decimal('55'))
    >>> pick_plan_category2("Swisscom", "NATEL xtra infinity L", Decimal('89'))
    ('CAT Y4', Decimal('89'))
    >>> pick_plan_category2("Swisscom", "NATEL infinity XL", Decimal('169'))
    ('CAT V 169', Decimal('169'))
    >>> pick_plan_category2("Sunrise", "Flex 250", Decimal('85'))
    Traceback (most recent call last):
      ...
    InvalidCategory: Category not found for: Sunrise, flex 250, 85
    >>> pick_plan_category2("Sunrise", "Flex 250", Decimal('90'))
    Traceback (most recent call last):
      ...
    InvalidCategory: Category not found for: Sunrise, flex 250, 90
    >>> pick_plan_category2("Sunrise", "Flex 250", Decimal('90'), True)
    Traceback (most recent call last):
      ...
    InvalidCategory: Category not found for: Sunrise, flex 250, 90
    >>> pick_plan_category2("Sunrise", "flex Basic", Decimal('20'))
    Traceback (most recent call last):
      ...
    InvalidCategory: Category not found for: Sunrise, flex Basic, 20
    """
    plan_name = _fix_planname(plan_name, operator)
    plan_category_mappings = load_plan_category_mappings()

    def filter_category_mapping(x):
        return x['operator'].lower() == operator.lower() and x['price plan'].lower() == plan_name.lower()
    rows = filter(filter_category_mapping, plan_category_mappings)
    if len(rows) < 1:
        logging.error("Category not found for: %s, %s, %s" % (operator, plan_name, per_month))
        raise InvalidCategory("Category not found for: %s, %s, %s" % (operator, plan_name, per_month))
    if len(rows) > 1:
        logging.error("More than 1 category found: %s, %s, %s" % (operator, plan_name, per_month))
        raise InvalidCategory("More than 1 category found: %s, %s, %s" % (operator, plan_name, per_month))
    res = rows[0]
    if Decimal(res['recurring charge']) != Decimal(per_month):
        if not ignore_rec_charge_diff:
            logging.error("Price plan has invalid price: %s, %s, %s. Has: %s, should: %s" %
                                  (operator, plan_name, per_month, per_month, res['recurring charge']))
            raise InvalidRecurringChargeForPricePlan("Price plan has invalid price: %s, %s, %s. Has: %s, should: %s" %
                                  (operator, plan_name, per_month, per_month, res['recurring charge']))
        else:
            per_month = Decimal(res['recurring charge'])

    return res['category'], per_month

def _guess_brand(product_info):
    branded_devices = load_branded_devices()
    for branded_device in branded_devices:
        if branded_device['device'].lower() in product_info['device_name'].lower():
            return branded_device['brand']
    return None

def _pick_brand(product_info):
    """
    >>> _pick_brand({'brand': '', 'device_name': 'BlackBerry Q10 - LTE - QWERTZ - Schwarz'})
    'BlackBerry'
    >>> _pick_brand({'brand': '', 'device_name': 'Blackberry Z10 black Swisscom 4G'})
    'BlackBerry'
    """
    if product_info['brand']:
        return product_info['brand']
    brands = load_brands()
    for brand in brands:
        if brand.lower() in product_info['device_name'].lower():
            return brand
    brand = _guess_brand(product_info)
    if brand:
        return brand
    logging.error("Brand not found for:\n%s" % str(product_info))
    return ''

def _fix_operator(operator):
    if operator.lower() in 'M-Budget Mobile'.lower():
        return 'M-Budget Mobile'
    return operator

def _strip_operator(device_name):
    """
    >>> _strip_operator('iPhone 4S 16Gb Orange')
    'iPhone 4S 16Gb'
    >>> _strip_operator('Samsung Galaxy Swisscom')
    'Samsung Galaxy'
    >>> _strip_operator('Nokia N99 m-budget')
    'Nokia N99'
    >>> _strip_operator('Nokia Lumia 920 Yellow MBudget')
    'Nokia Lumia 920 Yellow'
    """
    for operator in operator_names:
        m = re.search(operator, device_name, re.I)
        if m:
            found = m.group(0)
            device_name = re.sub(found, '', device_name)
    return device_name.strip()

def _filter_samsung_model_number(device_name, brand=None):
    """
    >>> _filter_samsung_model_number('Apple iPhone 4S')
    'Apple iPhone 4S'
    >>> _filter_samsung_model_number('Samsung GT-I9505 GALAXY S4 (16GB)')
    'Samsung GALAXY S4 (16GB)'
    >>> _filter_samsung_model_number('Samsung GT-I9505')
    'Samsung GT-I9505'
    >>> _filter_samsung_model_number('Samsung GT-N7100 GALAXY Note 2')
    'Samsung GALAXY Note 2'
    >>> _filter_samsung_model_number('Samsung E1150')
    'Samsung E1150'
    >>> _filter_samsung_model_number('Samsung SM-N9005 Galaxy Note 3')
    'Samsung Galaxy Note 3'
    >>> _filter_samsung_model_number('Samsung E1150 4Gb')
    'Samsung E1150 4Gb'
    >>> _filter_samsung_model_number('Galaxy Note 3 N9005 32Gb', 'Samsung')
    'Galaxy Note 3 32Gb'
    >>> _filter_samsung_model_number('Samsung SM-A500 GALAXY A5')
    'Samsung GALAXY A5'
    """
    if 'samsung' not in device_name.lower() and (brand is None or 'samsung' not in brand.lower()):
        return device_name

    # strip stop words: 3G, 4G, memory
    res = _remove_gb(device_name)
    res = res.replace('3g', '').replace('3G', '')\
        .replace('4g', '').replace('4G', '')\
        .replace('4g+', '').replace('4G+', '').strip()
    res = fix_spaces(res)

    m = re.search(r'((\w{2}-)?\w\d{3,4}\w?).*', res)

    if m:
        found = m.group(1)
        res = res.replace(found, '')
        if res.strip().lower() == 'samsung' or res.strip().lower() == '':
            return device_name
        res = device_name.replace(found, '')
        res = fix_spaces(res)
        return res

    return device_name

def _fix_device_capitalization(device_name):
    matches = [
        ('iphone', 'iPhone'),
        ('ipad', 'iPad'),
        ('iii', 'III'),
        ('ii', 'II'),
        ('iv', 'IV')
    ]
    for m1, m2 in matches:
        if m1.title() in device_name:
            device_name = device_name.replace(m1.title(), m2)

    # samsung model numbers
    m = re.search(r'(gt)?(\w)(\d{4}\w?)', device_name, re.I)
    if m:
        found = m.group(0)
        gt = m.group(1) or ''
        letter = m.group(2) or ''
        number = m.group(3) or ''
        if letter and number:
            fixed_model_number = letter.capitalize() + number
            if gt:
                fixed_model_number = gt.upper() + '-' + fixed_model_number
            device_name = device_name.replace(found, fixed_model_number)
    return device_name

def _fix_samsung_galaxy_name(device_name):
    """
    >>> _fix_samsung_galaxy_name('Samsung Galaxy S+')
    'Samsung Galaxy S Plus'
    >>> _fix_samsung_galaxy_name('S4 Active')
    'Galaxy S4 Active'
    """
    matches = {
        'S II': ('S 2', 'S2', 'S II', 'SII'),
        'S III': ('S 3', 'S3', 'S III', 'SIII'),
        'S4': ('S 4', 'S4', 'S IV', 'SIV'),
        'Note II': ('Note 2', 'Note2', 'Note II', 'NoteII'),
        'S Plus': ('S\+', 'S \+'),
        'S II Plus': ('S II\+', 'S II \+', 'SII\+', 'SII \+'),
    }
    if not 'galaxy' in device_name.lower() and 's4 active' in device_name.lower():
        return 'Galaxy ' + device_name
    if not 'galaxy' in device_name.lower():
        return device_name
    for key, variants in matches.items():
        for var in variants:
            m = re.search(var, device_name, re.I)
            if m:
                found = m.group(0)
                return device_name.replace(found, key)
    return device_name

def remove_brand(device_name, brand):
    """
    >>> remove_brand('lg nexus 5', 'lg')
    'nexus 5'
    >>> remove_brand('lg nexus 5', 'lg electronics')
    'nexus 5'
    """
    brand_subs = [brand]
    for synonyms in brand_synonyms:
        if brand.lower() in synonyms:
            brand_subs = synonyms
            break

    for brand_sub in brand_subs:
        m = re.search("by %s" % brand_sub, device_name, re.I)
        if m:
            found = m.group(0)
            device_name = re.sub(found, '', device_name)

        m = re.search(brand_sub, device_name, re.I)
        if m:
            found = m.group(0)
            device_name = re.sub(found, '', device_name)

    device_name = device_name.strip()

    return device_name

def fix_gb(device_name):
    regex = '(\d+) ?Gb'
    m = re.search(regex, device_name, re.I)
    if m:
        found = m.group(0)
        digit = m.group(1)
        device_name = device_name.replace(found, " %sGb" % digit)
        device_name = device_name.strip()
    return device_name

def _remove_gb(device_name):
    """
    >>> _remove_gb('Samsung E1150 8Gb')
    'Samsung E1150'
    """
    regex = '\d+Gb'
    m = re.search(regex, device_name, re.I)
    if m:
        found = m.group(0)
        res = device_name.replace(found, '').strip()
        res = fix_spaces(res)
    else:
        res = device_name
    return res

def _remove_lte(device_name):
    regex = ' Lte'
    m = re.search(regex, device_name, re.I)
    if m:
        found = m.group(0)
        device_name = device_name.replace(found, "")
        device_name = device_name.strip()

    return device_name


def _filter_swisscom_device_name(device_name):
    m = re.search('4G\+', device_name, re.IGNORECASE)
    if m:
        part = m.group(0)
        device_name = device_name.replace(part, '').strip()
    return device_name


def _fix_device_name(device_name, brand, strip_operator=False):
    """
    >>> _fix_device_name('Samsung GT-I9505 GALAXY S4 (16GB) ', u'Samsung')
    'Galaxy S4 16Gb'
    >>> _fix_device_name('Samsung GT-I9505 GALAXY S4 16GB ', u'Samsung')
    'Galaxy S4 16Gb'
    >>> _fix_device_name('Samsung GT-I9505 GALAXY S4 16 GB ', u'Samsung')
    'Galaxy S4 16Gb'
    >>> _fix_device_name('Samsung GALAXY S 3 (16GB) ', u'Samsung')
    'Galaxy S III 16Gb'
    >>> _fix_device_name('Samsung GT-I9505 GALAXY S 4 (16GB) ', u'Samsung')
    'Galaxy S4 16Gb'
    >>> _fix_device_name('Apple iPhone 5 - (16Gb)', 'Apple')
    'iPhone 5 16Gb'
    >>> _fix_device_name('Samsung GALAXY Note 2 (16GB) ', u'Samsung')
    'Galaxy Note II 16Gb'
    >>> _fix_device_name('Samsung Ativ S', u'Samsung')
    'Ativ S'
    >>> _fix_device_name('Samsung GT-B2710', u'Samsung')
    'GT-B2710'
    >>> _fix_device_name('BlackBerry Q10 - LTE - QWERTZ - Schwarz', 'Blackberry')
    'Q10 Lte Qwertz'
    >>> _fix_device_name('BlackBerry Q10 - LTE - QWERTZ - Schwarz', '')
    'Blackberry Q10 Lte Qwertz'
    >>> _fix_device_name('Lumia 920 32Gb Rot', 'Nokia')
    'Lumia 920 32Gb'
    >>> _fix_device_name('Samsung E1150 Titanium Silver', 'Samsung')
    'E1150'
    >>> _fix_device_name('Samsung SM-N9005 Galaxy Note 3', 'Samsung')
    'Galaxy Note 3'
    >>> _fix_device_name('S4 Active', 'Samsung')
    'Galaxy S4 Active'
    >>> _fix_device_name('Samsung S6312 Galaxy Young Duos 4Gb', 'Samsung')
    'Galaxy Young Duos 4Gb'
    >>> _fix_device_name('Galaxy Note 3 N9005 32Gb', 'Samsung')
    'Galaxy Note 3 32Gb'
    >>> _fix_device_name('Moto G (2nd Gen) (8GB, Dual SIM, Schwarz)', 'Motorola')
    'Moto G 2Nd Gen 8Gb Dual Sim'
    >>> _fix_device_name('Samsung Galaxy S5 4G+', 'Samsung')
    'Galaxy S5'
    """
    # do not filter colour for Archos devices
    if 'Archos'.lower() not in brand.lower():
        device_name = filter_color(device_name)

    if strip_operator or 'iphone' in device_name.lower():
        device_name = _strip_operator(device_name)

    device_name = _filter_swisscom_device_name(device_name)
    device_name = _filter_samsung_model_number(device_name, brand)
    device_name = _fix_samsung_galaxy_name(device_name)
    device_name = remove_brand(device_name, brand)
    device_name = remove_punctuation(device_name)
    device_name = fix_gb(device_name)
    device_name = fix_spaces(device_name)
    device_name = device_name.title()
    device_name = _fix_device_capitalization(device_name)
    return device_name

def _fix_planname(plan_name, operator):
    """
    >>> _fix_planname("Comfort 15 [A]", "Orange")
    'Comfort 15'
    >>> _fix_planname("Orange Young Star [Dy]", "Orange")
    'Young Star'
    >>> _fix_planname("NATEL libery primo + Blackberry Option", "Swisscom")
    'Natel libery primo'
    >>> _fix_planname("Mbudget Mobile Basic", "M-Budget Mobile")
    'Basic'
    >>> _fix_planname("Orange Young Star", "Orange")
    'Young Star'
    >>> _fix_planname("Unl. Int. / Surf 10 / Priority [G]", "Orange")
    'Me Unlim. International / Surf 10 / Priority'
    >>> _fix_planname("Me sw60,surf10,priority", "Orange")
    'Me Swiss 60 / Surf 10 / Priority'
    >>> _fix_planname("Me unl.tr,surfDaily,relaxPlus", "Orange")
    'Me Unlim. Travel / Surf Daily / Relax Plus'
    >>> _fix_planname("Unlim.International, Surf 10, Relax Plus", "Orange")
    'Me Unlim. International / Surf 10 / Relax Plus'
    >>> _fix_planname(u'Unl.International, Surf 10, Relax Plus', 'Orange')
    'Me Unlim. International / Surf 10 / Relax Plus'
    >>> _fix_planname('sw60,surf3,service', 'Orange')
    'Me Swiss 60 / Surf 3 / Service'
    >>> _fix_planname('Me unl.sms,surfDaily,service', 'Orange')
    'Me Unlim. SMS / Surf Daily / Service'
    >>> _fix_planname("Unl. Int. / Surf 10 / Service", "Orange")
    'Me Unlim. International / Surf 10 / Service'
    >>> _fix_planname("Abo Surf Advanced", "M-Budget Mobile")
    'Surf Advanced'
    >>> _fix_planname(u'Orange Me Unlimited SMS, Surf 3, Priority', "Orange")
    'Me Unlim. SMS / Surf 3 / Priority'
    >>> _fix_planname('Orange Young Star, Relax', 'Orange')
    'Young Star, Relax'
    >>> _fix_planname('Orange Young Star, Service', 'Orange')
    'Young Star'
    >>> _fix_planname(u'Orange Me Unlimited Orange, Surf 2, Priority', "Orange")
    'Me Unlim. Orange / Surf 2 / Priority'
    >>> _fix_planname(u'Orange Me Unlimited Orange 60, Surf 2, Priority', "Orange")
    'Me Unlim. Orange 60 / Surf 2 / Priority'
    >>> _fix_planname(u'Orange Me Unlimited Roaming, Surf 2, Priority', "Orange")
    'Me Unlim. Roaming / Surf 2 / Priority'
    >>> _fix_planname(u'Unl. Orange 60, Surf 1, Relax Plus', 'Orange')
    'Me Unlim. Orange 60 / Surf 1 / Relax Plus'
    >>> _fix_planname(u'Plus Plus Start', 'Orange')
    'Plus Start'
    """
    remove_words = ['+ Blackberry Option', 'Blackberry']
    for word in remove_words:
        if word in plan_name:
            plan_name = plan_name.replace(word, "")
    plan_name = plan_name.strip()
    import HTMLParser
    h = HTMLParser.HTMLParser()
    res = h.unescape(plan_name)
    while res != h.unescape(res):
        res = h.unescape(res)

    res = res.encode("ascii", "ignore")

    regex = '\[[ABCDEFG]{1}y?\]'
    m = re.search(regex, res, re.I)
    if m:
        found = m.group(0)
        res = res.replace(found, '')
        res = res.strip()

    regex = 'MBudget'
    m = re.search(regex, res, re.I)
    if m:
        found = m.group(0)
        res = res.replace(found, 'M-Budget')
        res = res.strip()

    regex = '%s - ' % operator
    m = re.search(regex, res, re.I)
    if m:
        found = m.group(0)
        res = res.replace(found, '')
        res = res.strip()

    regex = '%s' % operator
    m = re.search(regex, res, re.I)
    if m:
        found = m.group(0)
        res = res.replace(found, '')
        res = res.strip()

    regex = 'NATEL'
    m = re.search(regex, res, re.I)
    if m:
        found = m.group(0)
        res = res.replace(found, 'Natel')
        res = res.strip()

    regex = 'flat'
    m = re.search(regex, res, re.I)
    if m:
        found = m.group(0)
        res = res.replace(found, 'flat')
        res = res.strip()

    regex = 'flex'
    m = re.search(regex, res, re.I)
    if m:
        found = m.group(0)
        res = res.replace(found, 'flex')
        res = res.strip()

    regex = 'M-Budget'
    m = re.search(regex, res, re.I)
    if m:
        found = m.group(0)
        res = res.replace(found, '')
        res = res.strip()

    if operator == 'Orange':
        found_split = False
        regex_digitec = '(.*) \/ (.*) \/ (.*)'
        m_digitec = re.search(regex_digitec, res, re.I)
        regex_mobilezone = '(Me )?([^\s]*),(.*),(.*)'
        m_mobilezone = re.search(regex_mobilezone, res, re.I)
        regex_orange = '(.*),(.*),(.*)'
        m_orange = re.search(regex_orange, res, re.I)
        # digitec
        if m_digitec:
            found_split = True
            a = m_digitec.group(1)
            b = m_digitec.group(2)
            c = m_digitec.group(3)

            if a == 'Unl. Int.':
                a = 'Unl. International'

            regex = 'Releax'
            m = re.search(regex, c, re.I)
            if m:
                found = m.group(0)
                c = c.replace(found, 'Relax')

            regex = 'Serivce'
            m = re.search(regex, c, re.I)
            if m:
                found = m.group(0)
                c = c.replace(found, 'Service')

        # mobilezone
        elif ('surfdaily' in res.lower() or
                'surf0' in res.lower() or
                'surf1' in res.lower() or
                'surf3' in res.lower() or
                'surf10' in res.lower()) and \
                m_mobilezone:
            found_split = True
            # mobilezone
            a = m_mobilezone.group(2)
            b = m_mobilezone.group(3)
            c = m_mobilezone.group(4)

            if a == 'sw60':
                a = 'Swiss 60'
            elif a == 'unl.sms':
                a = 'Unlim. SMS'
            elif a == 'unl.sw':
                a = 'Unlim. Swiss'
            elif a == 'unl.tr':
                a = 'Unlim. Travel'
            elif a == 'unl.int':
                a = 'Unlim. International'
            else:
                raise Exception("Error while parsing Orange plan name: %s" % res)

            regex = 'surf(.*)'
            m = re.search(regex, b)
            if not m:
                raise Exception("Error while parsing Orange plan name: %s" % res)
            else:
                b = 'Surf ' + m.group(1)

            if c == 'relaxPlus':
                c = 'Relax Plus'
            elif 'priority' in c.lower():
                c = 'Priority'
            c = c.title()

            a = a.strip()
            b = b.strip()
            c = c.strip()

        elif m_orange:
            found_split = True
            # orange.ch
            a = m_orange.group(1)
            b = m_orange.group(2)
            c = m_orange.group(3)

            if a == 'Unlim.International' or a == 'Unl.International':
                a = 'Unlim. International'

            if c == 'relaxPlus':
                c = 'Relax Plus'
            elif 'priority' in c.lower():
                c = 'Priority'
            c = c.title()

            a = a.strip()
            b = b.strip()
            c = c.strip()

        if found_split:
            a = a.replace("  ", " ")
            # fix orange plan names
            regex = 'Me - '
            m = re.search(regex, a, re.I)
            if m:
                found = m.group(0)
                a = a.replace(found, 'Me ')
                a = a.strip()

            regex = "unlimited"
            m = re.search(regex, a, re.I)
            if m:
                found = m.group(0)
                a = a.replace(found, 'Unlim.')
                a = a.strip()
            m = re.search(regex, b, re.I)
            if m:
                found = m.group(0)
                b = b.replace(found, 'Unlim.')
                b = b.strip()

            regex = "\unlim'd\.?|unlim\.?|unl\.?"
            m = re.search(regex, a, re.I)
            if m:
                found = m.group(0)
                a = a.replace(found, 'Unlim.')
                a = a.strip()
            m = re.search(regex, b, re.I)
            if m:
                found = m.group(0)
                b = b.replace(found, 'Unlim.')
                b = b.strip()

            if not a.lower().startswith('me'):
                a = 'Me ' + a

            # Fix "Me Unlim. Orange"
            if a.strip() == 'Me Unlim.':
                a = 'Me Unlim. Orange'

            if a.strip() == 'Me Unlim. 60':
                a = 'Me Unlim. Orange 60'

            if b.strip() == 'Surf 250':
                b = 'Surf Start'

            res = a + ' / ' + b + ' / ' + c
        else:
            if 'young' in res.lower():
                regex = ", service"
                m = re.search(regex, res, re.I)
                if m:
                    found = m.group(0)
                    res = res.replace(found, '')
                    res = res.strip()

    # fix 'Abo' prefix in M-budget plans
    if operator == 'M-Budget' or operator == 'M-Budget Mobile':
        m = re.search('abo', res, re.I)
        if m:
            found = m.group(0)
            res = res.replace(found, '')
            res = res.strip()

    # fix "Plus" duplication
    reg = re.compile('plus plus', re.I)
    m = reg.search(res)
    while m is not None:
        found = m.group(0)
        replace = 'Plus' if found[0] == 'P' else 'plus'
        res = res.replace(found, replace)
        m = reg.search(res)

    return res

def _get_plan_identifier(plan_name):
    """
    >>> _get_plan_identifier('NOW max')
    'flat 6'
    >>> _get_plan_identifier("Me Unlim. Orange / Surf 1 / Service")
    'Me 0 Min, 0 SMS, 1 GB'
    >>> _get_plan_identifier("Me Unlim. Orange 60 / Surf 1 / Service")
    'Me 0 Min, 0 SMS, 3 GB'
    >>> _get_plan_identifier("Me Unlim. Roaming / Surf 1 / Service")
    'Me Unlim. Travel / Surf 1 / Service'
    >>> _get_plan_identifier("Me Unlim. International / Surf 2 / Service")
    'Me unlim. Min, unlim. SMS, 3 GB'
    >>> _get_plan_identifier("Me Unlim. International / Unlim. Surf / Service")
    'Me Unlim. International / Surf 10 / Service'
    >>> _get_plan_identifier("Me Unlim. International / Unlim. Surf Roaming / Service")
    'Me Unlim. International / Unlim. Surf Roaming / Service'
    >>> _get_plan_identifier("Me Unlim. Orange 60 / Unlim. Surf / Service")
    'Me unlim. Min, 0 SMS, 1 GB'
    """
    res = plan_name
    res = res.replace("Unlim. Orange 60 /", "Swiss 60 /")
    res = res.replace("Unlim. Salt 60 /", "Swiss 60 /")
    res = res.replace("Unlim. 60 /", "Swiss 60 /")
    res = res.replace("Unlim. Orange /", "Unlim. SMS /")
    res = res.replace("Unlim. Salt /", "Unlim. SMS /")
    res = res.replace("Unlim. Roaming /", "Unlim. Travel /")

    res = res.replace("/ Surf Start /", "/ Surf Daily /")
    res = res.replace("/ Surf 2 /", "/ Surf 3 /")
    res = res.replace("/ Unlim. Surf /", "/ Surf 10 /")

    res.replace("Salt", "Orange")

    plan_name = res

    new_old_mapping = load_new_old_plan_mapping()
    for row in new_old_mapping:
        new = row['new']
        old = row['old']
        if new.lower() == plan_name.lower():
            return old

    return res

def make_product_from_dict(response, product_info, operator, channel, plan_name, per_month, period, one_time_charge, strip_operator=False, ignore_rec_charge_diff=False):
    return make_product(ProductLoader(item=Product(), response=response), product_info, operator, channel, plan_name, per_month, period, one_time_charge, strip_operator, ignore_rec_charge_diff)

def make_product_from_response(response, operator, channel, plan_name, per_month, period, one_time_charge, strip_operator=False, ignore_rec_charge_diff=False):
    product_info = response.meta['product']
    return make_product_from_dict(response, product_info, operator, channel, plan_name, per_month, period, one_time_charge, strip_operator, ignore_rec_charge_diff)

def make_product_from_selector(hxs, product_info, operator, channel, plan_name, per_month, period, one_time_charge, strip_operator=False, ignore_rec_charge_diff=False):
    return make_product(ProductLoader(item=Product(), selector=hxs), product_info, operator, channel, plan_name, per_month, period, one_time_charge, strip_operator, ignore_rec_charge_diff)

def make_product(loader, product_info, operator, channel, plan_name, per_month, period, one_time_charge, strip_operator=False, ignore_rec_charge_diff=False):
    plan_name = _fix_planname(plan_name, operator)
    # fix orange to salt
    plan_name = plan_name.replace('Orange', 'Salt')
    # category, per_month = pick_plan_category2(operator, plan_name, per_month, ignore_rec_charge_diff)
    brand = _pick_brand(product_info)
    # fix device name when brand is already found
    device_name = _fix_device_name(product_info['device_name'], brand, strip_operator)
    period = re.search("\d+", period).group(0)
    one_time_charge = one_time_charge if one_time_charge else 0

    device_identifier = product_info['identifier'] if 'identifier' in product_info else device_name
    identifier_plan = _get_plan_identifier(plan_name)
    identifier = device_identifier + '_' + identifier_plan + '_' + period
    network_gen = product_info.get('network_gen', '')
    if network_gen:
        if '4g' in network_gen.lower():
            network_gen = '4G'
        else:
            network_gen = '3G'
    else:
        network_gen = ''
    # if network_gen:
    #     identifier += '_' + network_gen

    # loader = ProductLoader(item=Product(), response=response)
    loader.add_value('name', device_name)
    loader.add_value('url', product_info['url'])
    loader.add_value('brand', brand)
    loader.add_value('image_url', product_info['image_url'])
    # loader.add_value('category', category)

    loader.add_value('price', one_time_charge)
    loader.add_value('identifier', identifier)

    meta_loader = OrangeNewMetaLoader(item=OrangeNewMeta())

    meta_loader.add_value('device_name', remove_punctuation_and_spaces(device_name).lower())
    meta_loader.add_value('device_identifier', device_identifier)
    meta_loader.add_value('plan_name', plan_name)
    meta_loader.add_value('period', period)
    meta_loader.add_value('one_time_charge', one_time_charge)
    meta_loader.add_value('per_month', per_month)
    meta_loader.add_value('operator', operator)
    meta_loader.add_value('channel', channel)
    # meta_loader.add_value('category', category)

    meta_loader.add_value('network_gen', network_gen)

    if 'in_stock' in product_info:
        in_stock = product_info['in_stock']
        if isinstance(in_stock, bool):
            if not in_stock:
                loader.add_value('stock', 0)
        elif isinstance(in_stock, int):
            loader.add_value('stock', in_stock)

    product = loader.load_item()
    product['metadata'] = meta_loader.load_item()

    return product

colors_2words = [
    'ebony gray',
    'ebony grey',
    'pebble blue',
    'marble white',
    'chic white',
    'aluminium silver',
    'metallic black',
    'metallic silver',
    'warm grey',
    'warm gray',
    'chrome black',
    'phantom black',
    'warm silver',
    'golden white',
    'silver white',
    'rose red',
    'dynamic grey',
    'dynamic gray',
    'slate grey',
    'slate gray',
    'hot pink',
    'pearl white',
    'dark grey',
    'dark gray',
    'ceramic metal',
    'gradient metal',
    'classic silber',
    'classic silver',
    'modern black',
    'black mist',
    'white frost',
    'pure white',
    'stealth black',
    'polar white',
    'california blue',
    'dark brown',
    'titan grey',
    'titan gray',
    'met. silver',
    'glacial silver',
    'ruby wine',
    'ruby red',
    'neutral white',
    'flamenco red',
    'steel gray',
    'steel grey',
    'charcoral black',
    'charcoal black',
    'Titanium Silver',
    'black slate',
    'black & slate',
    'white & silver',
    'glossy brown',
    'space grey',
    'space gray',
    'high-rise gray/yellow',
    'domino black/white',
    'lime green',
    'electric blue',
    'shimmery white',
    'deep blue',
    'glamour red',
    'vivid blue',
    'amber gold',
    'gunmetal grey',
    'gunmetal gray',
    'space grey',
    'space gray',
    'space grau',
    'neo black',
    'silver on gold',
    'champagne gold',
    'midnight black',
    'pearl white',
    'platinum silver',
    'leather black',
]

colors = [
    'black',
    'white',
    'gray',
    'grey',
    'yellow',
    'blue',
    'silver',
    'red',
    'graphite',
    'graphit',
    'magenta',
    'cyan',
    'pink',
    'silber',
    'titanium',
    'brown',
    'garnet',
    'onyx',
    'sapphire',
    'metallic',
    'gold',
    'serene',
    'limelight',
    'limegreen',
    'atlantic',
    'domino/white',
    'high-rise/yellow',
    'orange',
    'indigo',
    'slate',
    'green',
    'violett',
    'purple',
    'ruby',
    'glamour',
    'deep',
    'vivid',
    'amber',
    'gunmetal',
    'space',

    # German colours
    u'schwarz',
    u'weiss',
    u'gelb',
    u'grün',
    u'burgundrot',
    u'burgund-rot',
    u'rot',
    u'blau',
    u'lila',
    u'silber',
    u'chrom',
    u'grau',
]

@cache
def filter_color(device_name):
    """
    >>> filter_color('Lumia 920 32Gb Rot')
    'Lumia 920 32Gb'
    >>> filter_color('Lumia 920 Amber Blue')
    'Lumia 920'
    >>> filter_color('Lumia 920 Ucla Blue')
    'Lumia 920'
    >>> filter_color('Sony Xperia Z2 - 16 GB - Violett')
    'Sony Xperia Z2 - 16 GB'
    >>> filter_color('Emporia CLICK (Schwarz)')
    'Emporia CLICK'
    """

    reg_groups = [
        [
            r'(.*) - %s( .*)?',
            r'(.*) %s( .*)?',
            r'(.*) \(%s\)( .*)?',
            r'(.+)%s( .*)?',
        ],
        [
            r'(.*) - %s( ?.*)',
            r'(.*) %s( ?.*)',
            r'(.*) \(%s\)( ?.*)',
            r'(.+)%s( ?.*)',
        ]
    ]
    res = device_name

    for regs in reg_groups:
        for color in colors_2words:
            for reg in regs:
                m = re.search(reg % color, res, re.I)
                if m:
                    parts = [x for x in m.groups() if x is not None]
                    res = ''.join(parts)

        for color in load_colors():
            for reg in regs:
                m = re.search(reg % color, res, re.I)
                if m:
                    parts = [x for x in m.groups() if x is not None]
                    res = ''.join(parts)

        for color in colors:
            for reg in regs:
                m = re.search(reg % color, res, re.I)
                if m:
                    parts = [x for x in m.groups() if x is not None]
                    res = ''.join(parts)

    return res

def filter_out_of_stocks(products):
    """
    Gets list of dicts like:
    {
        'device_name': 'Apple iPhone,
        'brand': 'Apple',
        'url': 'http://url',
        'image_url': 'http://image_url',
        'in_stock': True
    }
    Can have duplicate device names.
    Filters out of stock products if there is the same in stock product
    """
    uniques = {}
    # find duplicates
    for product in products:
        device_name = product['device_name']
        if device_name not in uniques:
            uniques[device_name] = product
            continue
        else:
            old_product = uniques[device_name]
            if not old_product['in_stock'] and product['in_stock']:
                uniques[device_name] = product

    return uniques.values()

def filter_duplicates_with_higher_price(products):
    """
    Checks if products have duplicate identifiers.
    For duplicates - picks smallest price and throws away highest.

    >>> p1 = {'identifier': 'asd', 'price': 2, 'name': 'ASD1'}
    >>> p2 = {'identifier': 'asd', 'price': 1, 'name': 'ASD2'}
    >>> p3 = {'identifier': 'qwe', 'price': 2, 'name': 'QWE'}
    >>> products = [p1, p2, p3]
    >>> res = filter_duplicates_with_higher_price(products)
    >>> res.sort(key=lambda x: x['identifier'])
    >>> len(res)
    2
    >>> res[0]['identifier'], res[0]['price'], res[0]['name']
    ('asd', 1, 'ASD2')
    >>> res[1]['identifier']
    'qwe'
    >>> ids = [x['identifier'] for x in res]
    >>> len(ids) == len(set(ids))
    True
    >>> p4 = {'identifier': 'asd', 'price': 2, 'name': 'ASD', 'stock': 0}
    >>> p5 = {'identifier': 'asd', 'price': 3, 'name': 'ASD2'}
    >>> products = [p4, p5, p3]
    >>> res = filter_duplicates_with_higher_price(products)
    >>> res.sort(key=lambda x: x['identifier'])
    >>> len(res)
    2
    >>> res[0]['identifier'], res[0]['price'], res[0]['name']
    ('asd', 3, 'ASD2')
    >>> res[1]['identifier']
    'qwe'
    >>> ids = [x['identifier'] for x in res]
    >>> len(ids) == len(set(ids))
    True
    """
    uniques = {}
    # find duplicates
    for product in products:
        identifier = product['identifier']
        if identifier not in uniques:
            uniques[identifier] = product
            continue
        else:
            old_product = uniques[identifier]
            old_in_stock = ('stock' in old_product and old_product['stock'] > 0) or (not 'stock' in old_product)
            new_in_stock = ('stock' in product and product['stock'] > 0) or (not 'stock' in product)
            if not old_in_stock and new_in_stock:
                uniques[identifier] = product
            elif old_product['price'] > product['price']:
                uniques[identifier] = product

    return uniques.values()

if __name__ == "__main__":
    import doctest
    doctest.testmod()
