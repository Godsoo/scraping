# -*- coding: utf-8 -*-
import inspect


def check_cls_attr_is_derived_from_base_class(cls, attr_name):
    base_cls = cls.__base__
    if not hasattr(base_cls, attr_name):
        return False
    return getattr(base_cls, attr_name) == getattr(cls, attr_name)

def check_cls_has_attr(cls, attr_name, method=False, overriden=True):
    if hasattr(cls, attr_name) and (inspect.ismethod(getattr(cls, attr_name)) == method):
        if overriden:
            # check method is overriden
            return not check_cls_attr_is_derived_from_base_class(cls, attr_name)
        else:
            return True
    else:
        return False


def change_cls_method(cls, method_name, new_method_name, new_method=None):
    # if not check_cls_has_attr(cls, method_name, method=True, overriden=True):
    #     return
    setattr(cls, new_method_name, getattr(cls, method_name))
    if check_cls_has_attr(cls, method_name, method=True, overriden=True):
        delattr(cls, method_name)
    if new_method is not None:
        setattr(cls, method_name, new_method)

def change_cls_base(cls, new_base):
    old_base = cls.__base__
    cls.__bases__ = (old_base, new_base)
