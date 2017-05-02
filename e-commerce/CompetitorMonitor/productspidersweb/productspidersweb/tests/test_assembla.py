# -*- coding: utf-8 -*-
import unittest

from pyramid import testing

class TestGetAuthHeader(unittest.TestCase):
    def _get_testee_func(self):
        from productspidersweb import assembla
        return assembla.__dict__['__get_auth_header']

    def test_no_assembla_dict(self):
        request = testing.DummyRequest()
        testee = self._get_testee_func()
        res = testee(request)
        self.assertIsNone(res)

    def test_assemlba_but_no_access_token(self):
        request = testing.DummyRequest()
        request.session['assembla'] = {}
        testee = self._get_testee_func()
        res = testee(request)
        self.assertIsNone(res)

    def test_access_token_no_authorized(self):
        request = testing.DummyRequest()
        request.session['assembla'] = {
            'access_token': 'sometoken'
        }
        testee = self._get_testee_func()
        res = testee(request)
        self.assertIsNone(res)

    def test_authorized_false(self):
        request = testing.DummyRequest()
        request.session['assembla'] = {
            'access_token': 'sometoken',
            'authorized': False
        }
        testee = self._get_testee_func()
        res = testee(request)
        self.assertIsNone(res)

    def test_valid(self):
        request = testing.DummyRequest()
        request.session['assembla'] = {
            'access_token': 'sometoken',
            'authorized': True
        }
        testee = self._get_testee_func()
        res = testee(request)
        self.assertIsNotNone(res)
        self.assertEqual(res, {'Authorization': 'Bearer ' + request.session['assembla']['access_token']})