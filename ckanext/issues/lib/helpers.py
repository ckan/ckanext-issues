from math import ceil

from pylons import config

from ckan.plugins import toolkit
from ckan.lib import helpers
from ckanext.issues.model import IssueFilter

ISSUES_PER_PAGE = (15, 30, 50)


def replace_url_param(new_params, alternative_url=None, controller=None,
                      action=None, extras=None):
    '''
    replace existing parameters with new ones

    controller action & extras (dict) are used to create the base url via
    :py:func:`~ckan.lib.helpers.url_for` controller & action default to the
    current ones

    This can be overriden providing an alternative_url, which will be used
    instead.
    '''
    params_cleaned = [(k, v) for k, v in toolkit.request.params.items()
                      if k not in new_params.keys()]
    params = set(params_cleaned)
    if new_params:
        params |= set(new_params.items())
    if alternative_url:
        return helpers._url_with_params(alternative_url, params)
    return helpers._create_url_with_params(params=params,
                                           controller=controller,
                                           action=action, extras=extras)


class Pagination(object):
    def __init__(self, page, per_page, total_count, show_left=2, show_right=2):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count
        self.show_left = show_left
        self.show_right = show_right

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_previous(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def show_previous(self):
        return self.page > 1 + self.show_left

    @property
    def show_next(self):
        return self.page < self.pages - self.show_right

    def iter_pages(self):
        for i in range(self.page - self.show_left,
                       self.page + self.show_right + 1):
            if i > 0 and i <= self.pages:
                yield i


def get_issue_filter_types():
    return [(f.value, k) for k, f in IssueFilter.__members__.items()]


def get_issues_per_page():
    try:
        issues_per_page = [int(i) for i in
                           config['ckan.issues.issues_per_page']]
    except (ValueError, KeyError):
        issues_per_page = ISSUES_PER_PAGE
    return issues_per_page

