# -*- coding: utf-8 -*-
import unittest

from product_spiders.custom_crawl_methods.utils import check_cls_has_attr, check_cls_attr_is_derived_from_base_class, \
    change_cls_method, change_cls_base

class TestCheckClsHasAttrFuncOnAttrs(unittest.TestCase):

    def test_false_if_not_have(self):
        class Child(object):
            pass

        self.assertFalse(check_cls_has_attr(Child, 'attr'))

    def test_false_if_has_method_with_the_same_name(self):
        class Child(object):
            def attr(self):
                print 'Child'

        self.assertFalse(check_cls_has_attr(Child, 'attr'))

    def test_true_if_has_attr(self):
        class Child(object):
            attr = 'Child'

        self.assertTrue(check_cls_has_attr(Child, 'attr'))

    def test_true_if_base_class_has_attr(self):
        class Parent(object):
            attr = 'Parent'

        class Child(Parent):
            pass

        self.assertTrue(check_cls_has_attr(Child, 'attr', overriden=False))

    def test_false_if_checkoverriden_and_base_class_has_attr(self):
        class Parent(object):
            attr = 'Parent'

        class Child(Parent):
            pass

        self.assertFalse(check_cls_has_attr(Child, 'attr', overriden=True))

    def test_true_if_checkoverriden_and_overriden_in_child(self):
        class Parent(object):
            attr = 'Parent'

        class Child(Parent):
            attr = 'Child'

        self.assertTrue(check_cls_has_attr(Child, 'attr', overriden=True))

    def test_true_if_checkoverriden_and_base_class_not_have_attr(self):
        class Parent(object):
            pass

        class Child(Parent):
            attr = 'Child'

        self.assertTrue(check_cls_has_attr(Child, 'attr', overriden=True))


class TestCheckClsHasAttrFuncOnMethods(unittest.TestCase):

    def test_false_if_not_have(self):
        class Child(object):
            pass

        self.assertFalse(check_cls_has_attr(Child, 'attr', method=True))

    def test_false_if_has_nonmethod_with_the_same_name(self):
        class Child(object):
            attr = 'Child'

        self.assertFalse(check_cls_has_attr(Child, 'attr', method=True))

    def test_true_if_has_method(self):
        class Child(object):
            def attr(self):
                print 'Child'

        self.assertTrue(check_cls_has_attr(Child, 'attr', method=True))

    def test_true_if_base_class_has_method(self):
        class Parent(object):
            def attr(self):
                print 'Parent'

        class Child(Parent):
            pass

        self.assertTrue(check_cls_has_attr(Child, 'attr', method=True, overriden=False))

    def test_false_if_checkoverriden_and_base_class_has_method(self):
        class Parent(object):
            def attr(self):
                print 'Parent'

        class Child(Parent):
            pass

        self.assertFalse(check_cls_has_attr(Child, 'attr', method=True, overriden=True))

    def test_true_if_checkoverriden_and_overriden_in_child(self):
        class Parent(object):
            def attr(self):
                print 'Parent'

        class Child(Parent):
            def attr(self):
                print 'Child'

        self.assertTrue(check_cls_has_attr(Child, 'attr', method=True, overriden=True))

    def test_true_if_checkoverriden_and_base_class_not_have_attr(self):
        class Parent(object):
            pass

        class Child(Parent):
            def attr(self):
                print 'Child'

        self.assertTrue(check_cls_has_attr(Child, 'attr', method=True, overriden=True))


class TestCheckClsAttrIsDerivedFromBaseClass(unittest.TestCase):
    def test_true_if_not_overriden(self):
        class Parent(object):
            attr = 'Parent'

        class Child(Parent):
            pass

        self.assertTrue(check_cls_attr_is_derived_from_base_class(Child, 'attr'))

    def test_false_if_overriden(self):
        class Parent(object):
            attr = 'Parent'

        class Child(Parent):
            attr = 'Child'

        self.assertFalse(check_cls_attr_is_derived_from_base_class(Child, 'attr'))

    def test_false_if_parent_not_have_attr(self):
        class Parent(object):
            pass

        class Child(Parent):
            attr = 'Child'

        self.assertFalse(check_cls_attr_is_derived_from_base_class(Child, 'attr'))

class TestChangeClsMethod(unittest.TestCase):
    def test_change_cls_method(self):
        class Child(object):
            def a(self):
                return 'child'

        self.assertTrue(check_cls_has_attr(Child, 'a', method=True, overriden=True))
        self.assertEqual(Child().a(), 'child')

        change_cls_method(Child, 'a', 'new_a')

        self.assertFalse(check_cls_has_attr(Child, 'a', method=True, overriden=True))
        self.assertTrue(check_cls_has_attr(Child, 'new_a', method=True, overriden=True))
        self.assertEqual(Child().new_a(), 'child')

    def test_change_cls_method_replaces_with_new(self):
        class Child(object):
            def a(self):
                return 'child'

        self.assertTrue(check_cls_has_attr(Child, 'a', method=True, overriden=True))
        self.assertEqual(Child().a(), 'child')

        change_cls_method(Child, 'a', 'new_a', lambda self: 'child2')

        self.assertTrue(check_cls_has_attr(Child, 'a', method=True, overriden=True))
        self.assertTrue(check_cls_has_attr(Child, 'new_a', method=True, overriden=True))
        self.assertEqual(Child().new_a(), 'child')
        self.assertEqual(Child().a(), 'child2')


class ChangeClsBaseClass(unittest.TestCase):
    def test_changes_base_class(self):
        class OldParent(object):
            pass

        class NewParent(object):
            pass

        class Child(OldParent):
            pass

        self.assertNotIn(NewParent, Child.__bases__)

        change_cls_base(Child, NewParent)

        self.assertEqual(NewParent, Child.__bases__[1])

    def test_keeps_old_base_as_first(self):
        class OldParent(object):
            pass

        class NewParent(object):
            pass

        class Child(OldParent):
            pass

        self.assertIn(OldParent, Child.__bases__)

        change_cls_base(Child, NewParent)

        self.assertEqual(OldParent, Child.__bases__[0])

    def test_calls_old_base_class_init_method(self):
        class OldParent(object):
            init_count = 0

            def __init__(self):
                OldParent.init_count += 1
                super(OldParent, self).__init__()

        class NewParent(object):
            init_count = 0

            def __init__(self):
                NewParent.init_count += 1
                super(NewParent, self).__init__()

        class Child(OldParent):
            init_count = 0

            def __init__(self):
                super(Child, self).__init__()
                Child.init_count += 1

        self.assertEqual(OldParent.init_count, 0)
        self.assertEqual(NewParent.init_count, 0)
        self.assertEqual(Child.init_count, 0)

        Child()
        self.assertEqual(OldParent.init_count, 1)
        self.assertEqual(NewParent.init_count, 0)
        self.assertEqual(Child.init_count, 1)

        change_cls_base(Child, NewParent)

        Child()
        self.assertEqual(OldParent.init_count, 2)
        self.assertEqual(NewParent.init_count, 1)
        self.assertEqual(Child.init_count, 2)