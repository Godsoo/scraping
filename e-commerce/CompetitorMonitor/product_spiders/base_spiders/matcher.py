'''
Fuzzy matcher using main ideas from fuzzywuzzy but doing more pre-processing.
1) Converts strings to lower-case as it greatly improves difflib match ratio
2) Rewrites plural/singular forms, abbreviations
3) Handles units of measurement before fuzzy matching.
    '10 kg' vs '1 kg' is just a single character difference to difflib
4) Runs a "spellchecker" to handle misspelled multi-word brand names (a common case in test data)
5) Runs fuzzyuzzy token_set_ratio() on strings transformed in previous steps
   This is not correct in general case ('fox jumps over dog', 'dog jumps over fox') but looks good
   enough for titles and product names.
5.1) if there are unmatched words in both strings, run stemmer on them and check for matches again
'''
import re

from decimal import Decimal
from operator import itemgetter
from collections import defaultdict

# Try to use C implementation of Levenshtein algorithm for string differences
try:
    from Levenshtein import ratio as cratio
    def _ratio(s1,  s2):
        return int(round(100.0 * cratio(s1, s2)))
except:
    from warnings import warn
#    warn('Please install python-Levenshtein for better performance')
    from difflib import SequenceMatcher
    def _ratio(s1,  s2):
        m = SequenceMatcher(None, s1, s2)
        return int(round(100.0 * m.ratio()))

# Try to use C implementation of stemmer
try:
    import Stemmer
    _stemmer = Stemmer.Stemmer('porter')
    def _stem(s):
        return _stemmer.stemWord(s)
except:
#    warn('Please install PyStemmer for better performance and results')
    try:
        from nltk import stem
        _stemmer = stem.PorterStemmer()
        def _stem(s):
            return _stemmer.stem(s)
    except:
        warn('Please install PyStemmer or NLTK for better performance and results')
        def _stem(s):
            return s

def _parse_number(number_str, multi=False):
    c_index = number_str.rfind(',')
    d_index = number_str.rfind('.')
    if c_index > -1 and d_index > -1:
        if c_index > d_index:
            return Decimal(number_str.replace('.', '').replace(',', '.'))
        elif d_index > c_index:
            return Decimal(number_str.replace(',', ''))
    elif c_index > -1:
        if len(number_str.split(',')[-1]) == 3:
            return Decimal(number_str.replace(',', ''))
        else:
            return Decimal(number_str.replace(',', '.'))
    elif d_index > -1:
        if len(number_str.split('.')[-1]) == 3:
            # Can't know for sure if it's thousand or decimal separator
            return (Decimal(number_str), Decimal(number_str.replace('.', '')))
        else:
            return Decimal(number_str)
    else:
        return Decimal(number_str)

_RE_NUM3 = re.compile('([\d]+)[-\s]+([\d]+)\s*/\s*([\d]+)')
_RE_NUM2 = re.compile('([\d]+)\s*/\s*([\d]+)')
_RE_NUM1 = re.compile('([\.,\d]+)')
_NUMS = '([\d]+)[-\s]+([\d]+)\s*/\s*([\d]+)|([\d]+)\s*/\s*([\d]+)|([\.,\d]+)'
def parse_number(number_str):
    try:
        m = _RE_NUM3.match(number_str)
        if m:
            return _parse_number(m.group(1)) + _parse_number(m.group(2)) / _parse_number(m.group(3))
        m = _RE_NUM2.match(number_str)
        if m:
            return _parse_number(m.group(1)) / _parse_number(m.group(2))
        m = _RE_NUM1.match(number_str)
        if m:
            return _parse_number(m.group(1), multi=True)
    except:
        pass
    return Decimal(0)
 
_UNITS = [
    (['kg', 'kilogram', 'kilograms', 'kilo', 'kgs'],    1.,     'weight'),
    (['g', 'gram', 'grams'],                            1000.,  'weight'),
    (['m', 'meter', 'meters'],                          1.,     'length'),
    (['cm', 'centimeters', 'centimeter'],               100.,   'length'),
    (['lb', 'pound', 'pounds', 'lbs'],                  2.204,  'weight'),
    (['inch', 'inches', '"', '\'\''],                   39.37,  'length'),
    (['feet', 'foot'],                                  3.281,  'length'),
    (['cap', 'capsules', 'capsule', 'caps'],            1.0,    'cap'),
    (['ct'],                                            1.0,    'cap'),
    (['tab', 'tablet', 'tablets', 'tabs'],              1.0,    'tab'),
    (['ct'],                                            1.0,    'tab'),
    (['l', 'litre'],                                    1.0,    'volume'),
    (['ml'],                                            1000.0, 'volume'),
    (['oz'],                                            33.814, 'volume'),
]

MATTRESS_SIZE = {
    'single': 'single',
    'twin': 'single',
    'double': 'double',
    'full': 'double',
    'queen': 'queen',
    'king': 'queen',
    'wide double': 'queen',
    'california king': 'california king',
    'king long': 'california king',
}

class Matcher:
    def __init__(self, log=None):
        self._re_words = re.compile('\w+')
        self._log = log
        self._tags = {}

        self._measure_min = Decimal(0.95)
        self._measure_max = Decimal(1.05)
        self._rewrites = {}
        for units, _, _ in _UNITS:
            # Dedicated to:
            # 'Pro Lab Advanced Caffeine - 60Tablets', 'THREE PACKS of Prolab Advanced Caffeine 60 Tablets'
            self._rewrites[units[0]] = set(units)

        self._units = []
        for unit, m, t in _UNITS:
            self._units.append((unit, Decimal(m), t, re.compile(r'(%s)\s*(%s)\b' % (_NUMS, '|'.join(unit)), flags=re.IGNORECASE)))

        self._units.append((['inch'], Decimal(m), 'length', re.compile(r'(%s)\s*(")' % _NUMS, flags=re.IGNORECASE)))
        self._units.append((['inch'], Decimal(m), 'length', re.compile(r"(%s)\s*('')" % _NUMS, flags=re.IGNORECASE)))

    def _prepare(self, s, data=None, important=None):
        ''' Precompiles search string (to speed up batch matching) '''
        text = s.lower()
        measures = self._extract_measures(text)
        if data is None:
            data = s 
        if important:
            iwords = []
            for words in important:
                iwords.extend(self._re_words.findall(words.lower()))
            important = iwords
        else:
            important = []
                    
        return (data, s, text, tuple(measures), tuple(important))

    def define_tag(self, tag, words):
        if not isinstance(words, dict):
            words = [w.lower() for w in words]
            words = dict(zip(words, words))

        compiled_words = {}
        for w, value in words.items():
            w = self._re_words.findall(w)
            compiled_words[tuple(w)] = value
            compiled_words[(''.join(w), )] = value

        self._tags[tag] = compiled_words

    def _extract_tagged(self, ordered_words, compiled_tag):
        result = []
        for words, value in compiled_tag.items():
            try: pos = ordered_words.index(words[0])
            except: continue
            matched = True
            for offset, w in enumerate(words):
                if len(ordered_words) <= pos + offset or ordered_words[pos + offset] != w:
                    matched = False
                    break
            result.append(value)
        return result

    def _match_tags(self, words1, words2):
        for _, compiled_tag in self._tags.items():
            tags1 = self._extract_tagged(words1, compiled_tag)
            tags2 = self._extract_tagged(words2, compiled_tag)
            if tags1 and tags2:
                if not set(tags1).intersection(set(tags2)):
                    return False
        return True

    def _extract_measures(self, text):
        result = []
        for unit, m, t, r in self._units:
            for match in r.finditer(text):
                nums = parse_number(match.group(1))
                if isinstance(nums, tuple):
                    for num in nums:
                        result.append((match.group(0), num, unit[0], m, t))
                else:
                    result.append((match.group(0), nums, unit[0], m, t))
        return result

    def extract_measures(self, text):
        result = []
        for m in self._extract_measures(text):
            result.append((m[0], m[1], m[2]))
        return result

    def debug(self, msg):
        if self._log:
            self._log(msg)

    def _ratio(self, s1,  s2):
        m = SequenceMatcher(None, s1, s2)
        return int(round(100.0 * m.ratio()))

    def _split_measures(self, text, measures):
        # Split 120g -> 120 g
        # Improves matching of 'USN Creatine X4 120cap'
        #                      'USN Creatine X4 Lean Muscle and Strength Capsules - Tub of 120'
        for s, num, unit, _, _ in measures:
            if ' ' not in s:
                text = re.sub(r'\b%s\b' % s, str(num)+' '+unit, text)
        return text

    def _measures_equal(self, num_a, mult_a, num_b, mult_b):
        # Convert to largest units (lowest multiplier)
        new_a, new_b = num_a, num_b
        new_a_rounded, new_b_rounded = new_a, new_b
        try:
            if mult_a < mult_b:
                new_b = new_b / mult_b * mult_a
                new_b_rounded = new_b.quantize(new_a)
            elif mult_a > mult_b:
                new_a = new_a / mult_a * mult_b
                new_a_rounded = new_a.quantize(new_b)

            if new_a_rounded == new_b_rounded \
                    or new_a * self._measure_min <= new_b <= new_a * self._measure_max:
                return True
        except:
            self.debug('Error while comparing %s and %s' % (new_a, new_b))
        return False

    def _match_measures(self, text1, text2, measures1, measures2):
        ''' Match measures using precompiled values '''
        for a, num_a, unit_a, mult_a, type_a in measures1:
            found, matched = False, False
            for b, num_b, unit_b, mult_b, type_b in measures2:
                if type_a != type_b: continue
                found = True
                matched1 = self._measures_equal(num_a, mult_a, num_b, mult_b)
                if matched1:
                    #Don't use end of word because it's not matched for inches (" or '')
                    text1 = re.sub(r'\b%s' % re.escape(a), str(num_a)+' '+unit_a, text1)
                    text2 = re.sub(r'\b%s' % re.escape(b), str(num_a)+' '+unit_a, text2)
                    matched = True
                    # Continue because sometimes the same measure appears twice in different units
                    #break
                    
            if found and not matched:
                return (False, text1, text2)

        text1 = self._split_measures(text1, measures1)
        text2 = self._split_measures(text2, measures2)
        return (True, text1, text2)

    def match_measures(self, main_text, text):
        ''' Match measures contained in string. Does not assign a ratio but just True/False '''
        _, main_text, text1, measures1, _ = self._prepare(main_text)
        _, text, text2, measures2, _ = self._prepare(text)
        res = self._match_measures(main_text, text, measures1, measures2)
        return res[0]

    def _rewrite_words(self, words1, words2, common):
        for replace, searches in self._rewrites.items():
            m1 = words1.intersection(searches)
            if not m1:
                continue
            m2 = words1.intersection(searches)
            if not m2:
                continue

            common.add(replace)
            words1 = words1.difference(m1)
            words2 = words2.difference(m2)

            if not words1 or not words1:
                break

    def _correct_words(self, words1, words2, common, diff1, diff2=None):
        """ Spellchecker for misspelled brands that are written as 1 or 2 words
            Calculates intersection and difference as well
        """
        if diff2 is None:
            diff2 = []
        i = 0
        n = len(words1)
#        set2 = set(words2)
        set2 = words2
        big_word2 = ''.join(words2)
        while i < n:
            word1 = words1[i]
            if not word1 in big_word2:
                diff1.append(word1)
                i += 1
                continue
            candid = [w for w in set2 if w.startswith(word1)]
            if word1 in candid:
                common.add(word1)
            elif candid:
                j = i + 2
                while j <= n:
                    new_word = u''.join(words1[i:j])
                    if new_word in candid:
                        words1[i:j] = [new_word]
                        common.add(new_word)
                        # And remove from previous difference
                        try: diff2.remove(new_word)
                        except: pass
                        n -= (j - i - 1)
                        break
                    j += 1
                else:
                    diff1.append(word1)
            else:
                diff1.append(word1)
            i += 1
        return words1

    def correct_words(self, words1, words2):
        ''' This is like spell checker for misspelled brands, etc.
            when two words are written as one
        '''
        words1 = list(words1)
        words2 = list(words2)
        common = set()
        dummy = []
        self._correct_words(words1, words2, common, dummy)
        self._correct_words(words2, words1, common, dummy)
        return words1, words2

    def match_ratio(self, main_text, text, important=None):
        """
        >>> matcher = Matcher()
        >>> r = matcher.match_ratio("B 250", "B250")
        >>> r > 90
        True
        >>> r = matcher.match_ratio("B250", "B 250")
        >>> r > 90
        True
        """
        return self._match_ratio(self._prepare(main_text, important=important), self._prepare(text))

    def _match_ratio(self, prep1, prep2):
        ''' Match using precomputed values '''
        r = self._match_ratio_impl(prep1, prep2)
        _, main_text, _, _, _ = prep1
        _, text, _, _, _ = prep2
        self.debug(u'FUZZ: "%s","%s",%s' % (
                    repr(main_text.replace('"', '""')).lstrip('u').strip('\''),
                    repr(text.replace('"', '""')).lstrip('u').strip('\''),
                    r
                    ))
        return r

    def _match_ratio_impl(self, prep1, prep2):
        _, _, text1, measures1, important1 = prep1
        _, _, text2, measures2, important2 = prep2

        measures_matched, text1, text2 = self._match_measures(text1, text2, measures1, measures2)
        if not measures_matched:
            return 0

        words1 = self._re_words.findall(text1)
        words2 = self._re_words.findall(text2)

        intersection = set()
        diff1to2 = []
        words1 = self._correct_words(words1, words2, intersection, diff1to2)
        diff2to1 = []
        words2 = self._correct_words(words2, words1, intersection, diff2to1)

        diff1to2 = set(diff1to2)
        diff2to1 = set(diff2to1)
        self._rewrite_words(diff1to2, diff2to1, intersection)

        # Try to reduce the difference by spell correction and stemming
        stemmed1 = set([_stem(w) for w in diff1to2])
        stemmed2 = set([_stem(w) for w in diff2to1])
        intersection.update(stemmed1.intersection(stemmed2))
        diff1to2 = stemmed1.difference(stemmed2)
        diff2to1 = stemmed2.difference(stemmed1)

        # If no common words till now, just give up
        if len(intersection) < max(min(len(words1), len(words2)) * 0.3, 1):
            return 0

        if not self._match_tags(words1, words2):
            return 0

        if not diff1to2 or not diff2to1:
            return 100

        # Before we go to difflib, add more weight to important words
        important = important1 + important2
        lintersection = list(intersection)
        ldiff1to2 = list(diff1to2)
        ldiff2to1 = list(diff2to1)
        for w in important:
            if w in intersection:
                lintersection.append(w)
            elif w in diff1to2:
                ldiff1to2.append(w)
            elif w in diff2to1:
                ldiff2to1.append(w)

        sorted_sect = u' '.join(sorted(lintersection))
        sorted_1to2 = u' '.join(sorted(ldiff1to2))
        sorted_2to1 = u' '.join(sorted(ldiff2to1))

        combined_1to2 = sorted_sect + ' ' + sorted_1to2
        combined_2to1 = sorted_sect + ' ' + sorted_2to1

        # strip
        sorted_sect = sorted_sect.strip()
        combined_1to2 = combined_1to2.strip()
        combined_2to1 = combined_2to1.strip()

        pairwise = [
            _ratio(sorted_sect, combined_1to2),
            _ratio(sorted_sect, combined_2to1)
# Does not seem to contribute much
#    ,      _ratio(combined_1to2, combined_2to1)
        ]

        return max(pairwise)

class MultiProductMatcher:
    def __init__(self, candidates, log=None, matcher=None):
        self._ops = 0
        if matcher:
            self._matcher = None
        else:
            self._matcher = Matcher(log)

        self._candidates = defaultdict(list)
        for candidate in candidates:
            name = candidate['name']
            brand = candidate['brand']
            sku = candidate['sku']
            self._candidates[self._matcher._prepare(brand)].append(self._matcher._prepare(name, candidate, [brand, sku]))

    def get_op_count(self):
        return self._ops

    def info(self):
        mi, ma = None, 0
        for key, values in self._candidates.items():
            if not mi:
                mi = len(values)
            mi = min(mi, len(values))
            ma = max(ma, len(values))
        return '%d portions, min %d max %d' % (len(self._candidates), mi, ma)

    def match(self, product, min_ratio=0):
        name = product['name']
        brand = product['brand']
        sku = product['sku']

        m1 = self._matcher._prepare(name, important=[brand, sku])
        b1 = self._matcher._prepare(brand)
        result = []

        for b2 in self._candidates.keys():
            if not brand or self._matcher._match_ratio_impl(b1, b2) >= 90:
                for m2 in self._candidates[b2]:
                    r = self._matcher._match_ratio_impl(m1, m2)
                    self._ops += 1
                    if r >= min_ratio:
                        result.append((m2[0], r))

        # Searched by brand, got nothing. Assume brand is incorrect and retry
        if not result and brand:
            for candidates in self._candidates.values():
                for m2 in candidates:
                    r = self._matcher._match_ratio_impl(m1, m2)
                    self._ops += 1
                    if r >= min_ratio:
                        result.append((m2[0], r))

        result.sort(key=itemgetter(1), reverse=True)
        return result

    def match_ratio(self, main_text, text):
        return self._matcher.match_ratio(main_text, text)
                
import unittest

class TestMatcher(unittest.TestCase):
    def matches(self, main_text, text):
        return self.assertGreater(self.matcher.match_ratio(main_text, text), 90)
    def not_matches(self, main_text, text):
        return self.assertLess(self.matcher.match_ratio(main_text, text), 90)

    def log(self, s):
        print s

    def setUp(self):
        #self.matcher = Matcher(self.log)
        self.matcher = Matcher()

    def testMeasures(self):
        self.assertEqual(self.matcher.extract_measures('There kg are 10 kg of nothing kg'), [('10 kg', Decimal('10'), 'kg')])
        self.assertEqual(self.matcher.extract_measures('There kg are 10kg of nothing kg'), [('10kg', Decimal('10'), 'kg')])
        self.assertEqual(self.matcher.extract_measures('There kg are 10kgof nothing kg'), [])
        self.assertEqual(set(self.matcher.extract_measures('There kg are 10 kg of nothing kg and 2 cm of something')),
                         {('10 kg', Decimal('10'), 'kg'), ('2 cm', Decimal('2'), 'cm')})
        self.assertEqual(set(self.matcher.extract_measures('There kg are 10kg of nothing kg and 2cm of something')),
                         {('10kg', Decimal('10'), 'kg'), ('2cm', Decimal('2'), 'cm')})
        
    def testMeasureCompare(self):
        self.assertTrue(self.matcher.match_measures('2 kg', '2kg'))

        self.assertTrue(self.matcher.match_measures('2 kg', '2000g'))
        self.assertTrue(self.matcher.match_measures('2 kg', '2060g'))

        self.assertTrue(self.matcher.match_measures('2000g', '2 kg'))
        self.assertTrue(self.matcher.match_measures('2060g', '2 kg'))

        # Fixme: not so clear about rounding vs truncate
        self.assertTrue(self.matcher.match_measures('2.1 kg', '2140g'))
        self.assertTrue(self.matcher.match_measures('2.1 kg', '2160g'))
        self.assertFalse(self.matcher.match_measures('2 kg', '1499g'))
        self.assertTrue(self.matcher.match_measures('2 kg', '1500g')) #rounding

        self.assertTrue(self.matcher.match_measures('2140g', '2.1 kg'))
        self.assertTrue(self.matcher.match_measures('2160g', '2.1 kg'))
        self.assertFalse(self.matcher.match_measures('1499g', '2 kg'))
        self.assertTrue(self.matcher.match_measures('1500g', '2 kg')) #rounding

        self.assertFalse(self.matcher.match_measures('2lb', '2 kg'))
        self.assertFalse(self.matcher.match_measures('2 kg', '2lb'))

        self.assertTrue(self.matcher.match_measures('1l', '1030ml'))
        self.assertTrue(self.matcher.match_measures('1l', '1,030ml'))
        self.assertTrue(self.matcher.match_measures('1l', '33 oz'))

        self.assertTrue(self.matcher.match_measures('1030ml', '1l'))
        self.assertTrue(self.matcher.match_measures('1,030ml', '1l'))
        self.assertTrue(self.matcher.match_measures('33 oz', '1l'))

        self.assertTrue(self.matcher.match_measures('5lb', '2.2kg'))
        self.assertTrue(self.matcher.match_measures('2.2kg', '5lb'))

    def testCorrection(self):
        ''' correct_words is case-sensitive but the real matcher use it lower-case strings '''
        self.assertTrue(self.matcher.correct_words(['SciMX', 'Grow'], ['Sci', 'MX', 'Grow']), [['SciMX', 'Grow'], ['SciMX', 'Grow']])
        self.assertTrue(self.matcher.correct_words(['Sci', 'MX', 'Grow'], ['SciMX', 'Grow']), [['SciMX', 'Grow'], ['SciMX', 'Grow']])
        self.assertTrue(self.matcher.correct_words(['Breed', 'Love'], ['BreedLove']), [['BreedLove'], ['BreedLove']])

    def testWeight(self):
        self.matches('2kg', '2 kg')
        self.matches('2 kg', '2 kg')
        self.matches('2 kg', '2kg')

    def testStemming(self):
        ''' This gets 100% match thanks to stemming, simple difflib is not enough '''
        self.assertEqual(self.matcher.match_ratio('cool flapjack', 'cool flapjacks'), 100)
        self.assertEqual(self.matcher.match_ratio('x sets subsets', 'x subset set'), 100)

    def testMS(self):
        self.matches("Sci Mx Omni MX hardcore 4kg Strawberry","Sci Mx Omni Mx Hardcore 4.060kg")
        self.not_matches('Sci Mx Omni MX hardcore 2kg Vanilla', '@')
        self.not_matches('@', 'Sci Mx Omni MX hardcore 2kg Vanilla')

        self.matches('Sci Mx Omni MX hardcore 2kg Vanilla', 'Sci-MX Nutrition Omni-MX Hardcore 2030 g Vanilla Mass, Bulk and Strength Shake Powder')
        self.matches('USN Creatine X4 120cap', 'USN Creatine X4 Lean Muscle and Strength Capsules - Tub of 120')
        self.matches('Pro Lab Advanced Caffeine - 60Tablets', 'THREE PACKS of Prolab Advanced Caffeine 60 Tablets')
        self.matches('BSN Syntha 6 5lbs Cookies and Cream', 'BSN Syntha-6 Cookies and Cream Powder 2.2kg')
        self.matches('Maximuscle Promax Diet - 1.2kg Banana', 'Maximuscle PROMAX DIET 1200g - ALL FLAVOURS - Weight Loss and Definition Shake Powder (BANANA)')
        #Casein vs Cassein
        #self.matches('USN Premium 8HR Casein 908g Vanilla', 'USN Premium 8 hr Cassein 908 g Vanilla Protein Shake Powder')

    def testMiniFigure(self):
        self.assertGreater(self.matcher.match_ratio('mini figures from', 'Shredder\'s Dragon Bike ONLY! From Lego Set 79101 NO Minifigures!'), 90)
        self.assertGreater(self.matcher.match_ratio('mini figures from', 'Shredder\'s Dragon Bike. Mini figure from Set 79101'), 90)
        self.assertGreater(self.matcher.match_ratio('mini figures from', 'LEGO Legends of Chima Leonidas Mini Figure From Cragger\'s Command Ship set #70006'), 90)

    def test3WordSpellCheck(self):
        # '20 x 38' -> '20x38'
        self.matches('High5 Energy Gel + Caffeine - 20 x 38g Orange', 'High5 Energy gel 20X38 g (Taste: Orange)')

    def testInches(self):
        self.matches('15"', '15\'\'')
        self.not_matches('0.25"', '2/4\'\'')
        self.matches('0.5"', '2/4\'\'')
        self.not_matches('1/4"', '2/4\'\'')
        self.matches('15 "', '15 \'\'')
        self.not_matches('1/4 "', '2/4 \'\'')
        self.matches('7.75"', '7 3/4"')
        self.matches('2-1 / 2"', '2.5"')

    def testTagging(self):
        self.matcher.define_tag('color', ('Blue', 'GrEen'))
        self.assertLess(self.matcher.match_ratio(
                    'just a long text with similar words except one: blue',
                    'just a long text with similar words except one: green'
                    ), 1)

if __name__ == '__main__':
    unittest.main()
