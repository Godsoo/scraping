import unittest
import sys

from ..validation.additional_changes import MaxLengthValidator, SKUChangeValidator
from ..validation.duplicate_identifiers import DuplicateIdentifierValidator
from ..changes import Change, PriceChange, AdditionalChange
from mock import MagicMock


class TestMaxLengthValidator(unittest.TestCase):
    def test_max_length_exceeded(self):
        change = AdditionalChange()
        change.change_data = MagicMock(return_value=(AdditionalChange.UPDATE,
                                                     {'changes': {'sku': ('1', '123')}}))

        validator = MaxLengthValidator(None, settings={'fields_max_length': {'sku': 2}})
        self.assertTrue([x for x in validator.validate(change)])

    def test_max_length_not_exceeded(self):
        change = AdditionalChange()
        change.change_data = MagicMock(return_value=(AdditionalChange.UPDATE,
                                                     {'changes': {'sku': ('1', '123')}}))

        validator = MaxLengthValidator(None, settings={'fields_max_length': {'sku': 5}})
        self.assertFalse([x for x in validator.validate(change)])


class TestSKUChangeValidator(unittest.TestCase):
    def test_sku_changed(self):
        change = AdditionalChange(el_old={'identifier': '1', 'sku': '1', 'url': ''},
                                  el_new={'identifier': '1', 'sku': '123', 'url': ''})

        change.change_data = MagicMock(return_value=(AdditionalChange.UPDATE,
                                                     {'changes': {'sku': ('1', '123')}}))

        validator = SKUChangeValidator(None)
        self.assertTrue([x for x in validator.validate(change)])

    def test_sku_changed_ignore(self):
        change = AdditionalChange(el_old={'identifier': '1', 'sku': '1', 'url': ''},
                                  el_new={'identifier': '1', 'sku': '123', 'url': ''})

        change.change_data = MagicMock(return_value=(AdditionalChange.UPDATE,
                                                     {'changes': {'sku': ('1', '123')}}))

        validator = SKUChangeValidator(None, settings={'ignore_additional_changes': 'sku'})
        self.assertFalse([x for x in validator.validate(change)])


class TestDuplicateIdentifierValidator(unittest.TestCase):
    def test_duplicate_identifier(self):
        first = {'identifier': 'test'}
        second = {'identifier': 'test'}
        validator = DuplicateIdentifierValidator()
        f = validator.validate(first)
        s = validator.validate(second)
        self.assertIsNone(f)
        self.assertIsNotNone(s)

    def test_non_duplicate_identifier(self):
        first = {'identifier': 'test'}
        second = {'identifier': 'test1'}
        validator = DuplicateIdentifierValidator()
        f = validator.validate(first)
        s = validator.validate(second)
        self.assertIsNone(f)
        self.assertIsNone(s)