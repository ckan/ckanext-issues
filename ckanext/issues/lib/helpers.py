from math import ceil

from pylons import config

from ckan import model
from ckan.plugins import toolkit
from ckan.lib import helpers
from ckanext.issues.model import IssueFilter
from ckanext.issues import model as issuemodel

ISSUES_PER_PAGE = (15, 30, 50)

log = __import__('logging').getLogger(__name__)


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

    return helpers._url_with_params(toolkit.request.path, params)


class Pagination(object):
    def __init__(self, page, per_page, total_count, show_left=2, show_right=2):
        '''
        Helper for displaying a page navigator.

        e.g. << 1 ... 3 4 [5] >>

        :param show_left/right: the number of pages either side of the current
                                one should be offered
        '''
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
    def show_previous_ellipsis(self):
        return self.page > 2 + self.show_left

    @property
    def show_previous(self):
        return self.page > 1 + self.show_left

    @property
    def show_next_ellipsis(self):
        '''Returns whether you should show "..." before the last page'''
        return self.page < self.pages - self.show_right - 1

    @property
    def show_next(self):
        '''Returns whether you should show last page (in addition to the
        iter_pages)'''
        return self.page < self.pages - self.show_right

    def iter_pages(self):
        for i in range(self.page - self.show_left,
                       self.page + self.show_right + 1):
            if i > 0 and i <= self.pages:
                yield i


def get_issue_filter_types():
    return [(toolkit._(f.value), k) for k, f in IssueFilter.__members__.items()]


def get_issues_per_page():
    try:
        issues_per_page = [int(i) for i in
                           config['ckan.issues.issues_per_page']]
    except (ValueError, KeyError):
        issues_per_page = ISSUES_PER_PAGE
    return issues_per_page


def issues_enabled(dataset):
    '''Returns whether issues are enabled for the given dataset (dict)'''
    # config options allow you to only enable issues for particular datasets or
    # organizations
    datasets_with_issues_enabled = set(toolkit.aslist(
        config.get('ckanext.issues.enabled_for_datasets')
    ))
    organizations_with_issues_enabled = set(toolkit.aslist(
        config.get('ckanext.issues.enabled_for_organizations')
    ))
    if datasets_with_issues_enabled or organizations_with_issues_enabled:
        if datasets_with_issues_enabled and \
                dataset['name'] in datasets_with_issues_enabled:
            return True
        elif organizations_with_issues_enabled and \
                (dataset.get('organization') or {}).get('name') in \
                organizations_with_issues_enabled:
            return True
        return False
    else:
        extras = dataset.get('extras', [])
        for extra in extras:
            if extra.get('key') == 'issues_enabled':
                return toolkit.asbool(extra.get('value'))
        else:
            return toolkit.asbool(
                config.get('ckanext.issues.enabled_without_extra', True)
            )

def issues_enabled_for_organization(organization):
    '''Returns whether issues are enabled for the given organization (dict)'''
    organizations_with_issues_enabled = set(toolkit.aslist(
        config.get('ckanext.issues.enabled_for_organizations')
    ))
    if organizations_with_issues_enabled:
        return organization and \
            organization.get('name') in organizations_with_issues_enabled
    return True

def issues_list(dataset_ref, status=issuemodel.ISSUE_STATUS.open):
    '''
    Returns list of issue dicts.

    This is just basic - no options for sorting, closed issues, abuse. No
    pagination. For those, use the issues home page.
    '''
    if status not in issuemodel.ISSUE_STATUS:
        log.error('issues_list status must be open or closed - got %s', status)
        status = 'open'
    params = dict(dataset_id=dataset_ref,
                  status=getattr(issuemodel.ISSUE_STATUS, status),
                  sort='newest',
                  visibility=None,
                  q='')

    issues = toolkit.get_action('issue_search')(data_dict=params)
    return issues


def issues_user_has_reported_issue(user, abuse_reports):
    '''Returns whether the given user is among the given list of an issue's
    abuse_reports'''
    user_obj = model.User.get(user)
    if user_obj:
        return user_obj.id in abuse_reports
    else:
        return False


def issues_users_who_reported_issue(abuse_reports):
    '''Returns a list of users (dicts) who reported an issue/comment as
    spam/abuse'''
    users = []
    for user_id in abuse_reports:
        try:
            users.append(toolkit.get_action('user_show')(data_dict={'id':
                                                                    user_id}))
        except toolkit.ObjectNotFound:
            users.append(user_id)
    return users


def get_site_title():
    # older ckans
    site_title = config.get('ckan.site_title')
    try:
        # from ckan 2.4
        from ckan.model.system_info import get_system_info
        return get_system_info('ckan.site_title', site_title)
    except ImportError:
        return site_title


def get_issue_subject(issue):
    site_title = get_site_title()
    dataset = model.Package.get(issue['dataset_id'])
    msg = toolkit._('[%s Issue] %s')
    return msg % (site_title, dataset.title)


def issues_user_is_owner(user, dataset_id):
    if not user:
        # not logged in
        return False
    action = 'issue_admin'
    data_dict = {'dataset_id': dataset_id}
    # based on ckan.lib.helpers.check_access
    context = {'model': model,
               'user': user['name']}
    try:
        toolkit.check_access(action, context, data_dict)
        authorized = True
    except toolkit.NotAuthorized:
        authorized = False

    return authorized
