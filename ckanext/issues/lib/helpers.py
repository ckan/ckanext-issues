from math import ceil

from pylons import config

from ckan.plugins import toolkit
from ckan.lib import helpers
from ckanext.issues.model import IssueFilter
from ckanext.issues import model as issuemodel

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


def issues_enabled(dataset):
    datasets_with_issues_enabled = set(toolkit.aslist(
        config.get('ckanext.issues.enabled_for_datasets')
    ))
    # if the config option 'ckanext.issues.enabled_for_dataset' is
    # set with a list of datasets, only enabled for the listed datasets
    if datasets_with_issues_enabled:
        if dataset['name'] in datasets_with_issues_enabled:
            return True
    else:
        extras = dataset.get('extras')
        for extra in extras:
            if extra.get('key') == 'issues_enabled':
                return toolkit.asbool(extra.get('value'))
        else:
            return toolkit.asbool(
                config.get('ckanext.issues.enabled_per_dataset_default', True)
            )


def issues_list(dataset_ref):
    '''
    Returns list of issue dicts.

    This is just basic - no options for sorting, closed issues, spam. No
    pagination. For those, use the issues home page.
    '''
    params = dict(dataset_id=dataset_ref,
                  status=issuemodel.ISSUE_STATUS.open,
                  sort='newest',
                  spam_state=None,
                  q='')

    issues = toolkit.get_action('issue_search')(data_dict=params)
    return issues
