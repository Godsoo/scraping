# -*- coding: utf-8 -*-
import os.path
import json
from collections import OrderedDict

from models import SpiderRating

HERE = os.path.dirname(__file__)

# for reference
_field_types = ['simple', 'options', 'checkboxes']
_simple_field_types = ['regular', 'multiple']


_cache_metrics = None

def get_metrics_schema():
    global _cache_metrics
    if _cache_metrics is None:
        with open(os.path.join(HERE, 'spider_ratings_metrics.json')) as f:
            _cache_metrics = json.load(f, object_pairs_hook=OrderedDict)
    return _cache_metrics


def process_ratings_form(form):
    return _process_section(get_metrics_schema(), form)


def save_spider_rating(db_session, spider, params):
    spider_rating = db_session.query(SpiderRating).get(spider.id)
    if not spider_rating:
        spider_rating = SpiderRating()
        spider_rating.spider_id = spider.id

    spider_rating.params = params
    spider_rating.score = _calculate_rating(params)
    db_session.add(spider_rating)


def get_spider_rating_params(db_session, spider):
    spider_rating = db_session.query(SpiderRating).get(spider.id)
    if not spider_rating:
        return {}
    else:
        return spider_rating.params


def calculate_spider_rating(db_session, spider):
    params = get_spider_rating_params(db_session, spider)
    return _calculate_rating(params)


def _recursive_ordered_dict(raw):
    if not isinstance(raw, list):
        return raw
    if len(raw) < 1:
        return []
    if not isinstance(raw[0], tuple):
        return raw
    res = OrderedDict()
    for key, value in raw:
        if isinstance(value, list):
            res[key] = _recursive_ordered_dict(value)
        else:
            res[key] = value
    return res


def _process_section(metrics_conf, form, parents=None):
    if parents is None:
        parents = []
    res = {}
    for key in metrics_conf:
        form_key = ".".join(parents + [key])
        res[key] = _process_field(metrics_conf[key], form, form_key, parents + [key])
    return res

def _process_field(field_conf, form, form_key, parents):
    if field_conf['type'] == 'simple':
        if field_conf.get('type2') != 'multiple':
            return True if form.get(form_key) else False
        else:
            count_form_key = form_key + '-count'
            count = int(form.get(count_form_key, 0))
            if count == 0:
                return None
            # collect multiple values
            return [form["%s-%d" % (form_key, i)] for i in xrange(0, count)]
    elif field_conf['type'] == 'options':
        value = form.get(form_key)
        value_form_key = form_key + "." + value
        value_conf = field_conf['values'][value]
        if value_conf['type'] == 'simple':
            return {'value': value}
        else:
            return {
                'value': value,
                'subvalues': _process_field(value_conf, form, value_form_key, parents + [value])
            }
    elif field_conf['type'] == 'checkboxes':
        return _process_section(field_conf['values'], form, parents)


def _calculate_rating(params, metrics=None):
    if metrics is None:
        metrics = get_metrics_schema()
    field_scores = {}
    for key, field_data in params.items():
        if not field_data:
            continue
        if metrics[key]['score'] == 'formula':  # process formulas second time
            continue
        if isinstance(field_data, dict):
            if 'value' in field_data:
                value = field_data['value']
                value_metrics = metrics[key]['values'][value]
                field_scores[key] = _calculate_score_for_field(value_metrics)
                if 'subvalues' in field_data:
                    field_scores[key] += _calculate_rating(field_data['subvalues'], value_metrics['values'])
            else:
                field_scores[key] = _calculate_rating(field_data, metrics[key]['values'])
        elif isinstance(field_data, list):
            field_scores[key] = _calculate_score_for_field(metrics[key]) * len(field_data)
        else:
            field_scores[key] = _calculate_score_for_field(metrics[key])

    for key, field_data in params.items():
        if not field_data:
            continue
        if metrics[key]['score'] != 'formula':  # process only formulas
            continue
        if isinstance(field_data, dict):
            if 'value' in field_data:
                value = field_data['value']
                value_metrics = metrics[key]['values'][value]
                field_scores[key] = _calculate_score_for_field(value_metrics, field_scores)
                if 'subvalues' in field_data:
                    field_scores[key] = _calculate_rating(field_data['subvalues'], value_metrics['values'])
            else:
                field_scores[key] = _calculate_rating(field_data, metrics[key]['values'])
        elif isinstance(field_data, list):
            field_scores[key] = _calculate_score_for_field(metrics[key], field_scores) * len(field_data)
        else:
            field_scores[key] = _calculate_score_for_field(metrics[key], field_scores)

    return sum(field_scores.values())


def _calculate_score_for_field(field_conf, sibling_scores=None):
    score = field_conf['score']
    if score == 'formula':
        assert sibling_scores is not None, "Formula calculation needs siblings scores"
        res = field_conf['score_base']
        summand_score = field_conf['score_multiplier']
        for field in field_conf['score_summands']:
            res += summand_score * sibling_scores.get(field, 0) - sibling_scores.get(field, 0)
        return res
    else:
        return score