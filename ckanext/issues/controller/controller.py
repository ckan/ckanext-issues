import collections
from logging import getLogger
import re

from sqlalchemy import func
from pylons.i18n import _
from pylons import request, config, tmpl_context as c

from ckan.lib.base import BaseController, render, abort
import ckan.lib.helpers as h
from ckan.lib import mailer
import ckan.model as model
import ckan.logic as logic
import ckan.plugins as p
from ckan.plugins import toolkit

import ckanext.issues.model as issuemodel
from ckanext.issues.controller import show
from ckanext.issues.exception import ReportAlreadyExists
from ckanext.issues.lib import helpers as issues_helpers
from ckanext.issues.logic import schema
from ckanext.issues.lib.helpers import (Pagination, get_issues_per_page,
                                        get_issue_subject)

log = getLogger(__name__)

AUTOCOMPLETE_LIMIT = 10
VALID_CATEGORY = re.compile(r"[0-9a-z\-\._]+")
ISSUES_PER_PAGE = (15, 30, 50)


class IssueController(BaseController):
    def _before_dataset(self, dataset_id):
        '''Returns the dataset dict and checks issues are enabled for it.'''
        self.context = {'for_view': True}
        try:
            pkg = logic.get_action('package_show')(self.context,
                                                   {'id': dataset_id})
            # need this as some templates in core explicitly reference
            # c.pkg_dict
            c.pkg = pkg
            c.pkg_dict = c.pkg

            # keep the above lines to keep current code working till it's all
            # refactored out, otherwise, we should pass pkg as an extra_var
            # directly that's returned from this function
            if not issues_helpers.issues_enabled(pkg):
                abort(404, _('Issues have not been enabled for this dataset'))
            return pkg
        except logic.NotFound:
            abort(404, _('Dataset not found'))
        except p.toolkit.NotAuthorized:
            p.toolkit.abort(401,
                            _('Unauthorized to view issues for this dataset'))

    def _before_org(self, org_id):
        '''Returns the organization dict and checks issues are enabled for it.'''
        self.context = {'for_view': True}
        try:
            org = logic.get_action('organization_show')(self.context,
                                                        {'id': org_id})

            # we should pass org to the template as an extra_var
            # directly that's returned from this function
            if not issues_helpers.issues_enabled_for_organization(org):
                abort(404, _('Issues have not been enabled for this organization'))
            return org
        except logic.NotFound:
            abort(404, _('Dataset not found'))
        except p.toolkit.NotAuthorized:
            p.toolkit.abort(401,
                            _('Unauthorized to view issues for this organization'))

    def new(self, dataset_id, resource_id=None):
        dataset_dict = self._before_dataset(dataset_id)
        if not c.user:
            abort(401, _('Please login to add a new issue'))

        data_dict = {
            'dataset_id': dataset_dict['id'],
            'creator_id': c.userobj.id
        }
        try:
            logic.check_access('issue_create', self.context, data_dict)
        except logic.NotAuthorized:
            abort(401, _('Not authorized to add a new issue'))

        resource = model.Resource.get(resource_id) if resource_id else None
        if resource:
            data_dict['resource_id'] = resource.id

        c.errors, c.error_summary = {}, {}

        if request.method == 'POST':
            # TODO: ? use dictization etc
            #    data = logic.clean_dict(
            #        df.unflatten(
            #            logic.tuplize_dict(
            #                logic.parse_params(request.params))))
            data_dict.update({
                'title': request.POST.get('title'),
                'description': request.POST.get('description')
                })

            if not data_dict['title']:
                c.error_summary[_('title')] = [_("Please enter a title")]
            c.errors = c.error_summary

            if not c.error_summary:  # save and redirect
                issue_dict = logic.get_action('issue_create')(
                    data_dict=data_dict
                )
                h.flash_success(_('Your issue has been registered, '
                                  'thank you for the feedback'))
                p.toolkit.redirect_to(
                    'issues_show',
                    dataset_id=dataset_dict['name'],
                    issue_number=issue_dict['number'])

        c.data_dict = data_dict
        return render("issues/add.html")

    def show(self, issue_number, dataset_id):
        dataset = self._before_dataset(dataset_id)
        try:
            extra_vars = show.show(issue_number,
                                   dataset_id,
                                   session=model.Session)
        except toolkit.ValidationError, e:
            p.toolkit.abort(
                404, toolkit._(u'Issue not found: {0}').format(e.error_summary))
        except toolkit.ObjectNotFound, e:
            p.toolkit.abort(
                404, toolkit._(u'Issue not found: {0}').format(e))
        extra_vars['dataset'] = dataset
        return p.toolkit.render('issues/show.html', extra_vars=extra_vars)

    def edit(self, dataset_id, issue_number):
        self._before_dataset(dataset_id)
        issue = p.toolkit.get_action('issue_show')(
            data_dict={
                'issue_number': issue_number,
                'dataset_id': dataset_id,
            }
        )
        if request.method == 'GET':
            return p.toolkit.render(
                'issues/edit.html',
                extra_vars={
                    'issue': issue,
                    'errors': None,
                },
            )
        elif request.method == 'POST':
            data_dict = dict(request.params)
            data_dict['issue_number'] = issue_number
            data_dict['dataset_id'] = dataset_id
            try:
                p.toolkit.get_action('issue_update')(data_dict=data_dict)
                return p.toolkit.redirect_to('issues_show',
                                             issue_number=issue_number,
                                             dataset_id=dataset_id)
            except p.toolkit.ValidationError, e:
                errors = e.error_dict
                return p.toolkit.render(
                    'issues/edit.html',
                    extra_vars={
                        'issue': issue,
                        'errors': errors,
                    },
                )
            except p.toolkit.NotAuthorized, e:
                p.toolkit.abort(401, e.message)

    def comments(self, dataset_id, issue_number):
        # POST only
        if request.method != 'POST':
            abort(500, _('Invalid request'))

        dataset = self._before_dataset(dataset_id)

        auth_dict = {
            'dataset_id': c.pkg['id'],
            'issue_number': issue_number
            }
        # Are we not repeating stuff in logic ???
        try:
            logic.check_access('issue_create', self.context, auth_dict)
        except logic.NotAuthorized:
            abort(401, _('Not authorized'))

        next_url = h.url_for('issues_show',
                             dataset_id=c.pkg['name'],
                             issue_number=issue_number)

        # TODO: (?) move validation somewhere better than controller
        comment = request.POST.get('comment')
        if not comment or comment.strip() == '':
            h.flash_error(_('Comment cannot be empty'))
            p.toolkit.redirect_to(next_url)
            return

        # do this first because will error here if not allowed and do not want
        # comment created in that case
        if 'close' in request.POST or 'reopen' in request.POST:
            status = (issuemodel.ISSUE_STATUS.closed if 'close' in request.POST
                      else issuemodel.ISSUE_STATUS.open)
            issue_dict = {
                'issue_number': issue_number,
                'dataset_id': dataset['id'],
                'status': status
                }
            try:
                logic.get_action('issue_update')(self.context, issue_dict)
            except p.toolkit.NotAuthorized as e:
                p.toolkit.abort(401, e.message)
            if 'close' in request.POST:
                h.flash_success(_("Issue closed"))
            else:
                h.flash_success(_("Issue re-opened"))

        data_dict = {
            'author_id': c.userobj.id,
            'comment': comment.strip(),
            'dataset_id': dataset['id'],
            'issue_number': issue_number,
            }
        logic.get_action('issue_comment_create')(self.context, data_dict)

        p.toolkit.redirect_to(next_url)

    def dataset(self, dataset_id):
        """
        Display a page containing a list of all issues items for a dataset,
        sorted by category.
        """
        self._before_dataset(dataset_id)
        try:
            extra_vars = issues_for_dataset(dataset_id, request.GET)
        except toolkit.ValidationError, e:
            _dataset_handle_error(dataset_id, e)
        return render("issues/dataset.html", extra_vars=extra_vars)

    def delete(self, dataset_id, issue_number):
        dataset = self._before_dataset(dataset_id)
        if 'cancel' in request.params:
            p.toolkit.redirect_to('issues_show',
                                  dataset_id=dataset_id,
                                  issue_number=issue_number)

        if request.method == 'POST':
            try:
                toolkit.get_action('issue_delete')(
                    data_dict={'issue_number': issue_number,
                               'dataset_id': dataset_id}
                )
            except toolkit.NotAuthorized:
                msg = _(u'Unauthorized to delete issue {0}').format(
                    issue_number)
                toolkit.abort(401, msg)

            h.flash_notice(_(u'Issue has been deleted.'))
            p.toolkit.redirect_to('issues_dataset', dataset_id=dataset_id)
        else:
            return render('issues/confirm_delete.html',
                          extra_vars={
                              'issue_number': issue_number,
                              'pkg': dataset,
                          })

    def assign(self, dataset_id, issue_number):
        dataset = self._before_dataset(dataset_id)
        if request.method == 'POST':
            try:
                assignee_id = request.POST.get('assignee')
                assignee = toolkit.get_action('user_show')(
                    data_dict={'id': assignee_id})
            except toolkit.ObjectNotFound:
                h.flash_error(_(u'User {0} does not exist').format(assignee_id))
                return p.toolkit.redirect_to('issues_show',
                                             issue_number=issue_number,
                                             dataset_id=dataset_id)

            try:
                issue = toolkit.get_action('issue_update')(
                    data_dict={
                        'issue_number': issue_number,
                        'assignee_id': assignee['id'],
                        'dataset_id': dataset_id
                    }
                )

                notifications = p.toolkit.asbool(
                    config.get('ckanext.issues.send_email_notifications')
                )

                if notifications:
                    subject = get_issue_subject(issue)
                    msg = toolkit._("Assigned to %s")
                    body = msg % assignee['display_name']

                    user_obj = model.User.get(assignee_id)
                    try:
                        mailer.mail_user(user_obj, subject, body)
                    except mailer.MailerException, e:
                        log.debug(e.message)

            except toolkit.NotAuthorized:
                msg = _(u'Unauthorized to assign users to issue')
                toolkit.abort(401, msg)
            except toolkit.ValidationError, e:
                toolkit.abort(404)

        return p.toolkit.redirect_to('issues_show',
                                     issue_number=issue_number,
                                     dataset_id=dataset_id)

    def report(self, dataset_id, issue_number):
        dataset = self._before_dataset(dataset_id)
        if request.method == 'POST':
            if not c.user:
                msg = _('You must be logged in to report issues')
                toolkit.abort(401, msg)
            try:
                report_info = toolkit.get_action('issue_report')(
                    data_dict={
                        'issue_number': issue_number,
                        'dataset_id': dataset_id
                    }
                )
                if report_info:
                    # we have this info if it is an admin
                    msgs = [_('Report acknowledged.')]
                    if report_info['abuse_status'] == \
                            issuemodel.AbuseStatus.abuse.value:
                        msgs.append(_('Marked as abuse/spam.'))
                    msgs.append(_('Issue is visible.')
                                if report_info['visibility'] == 'visible' else
                                _('Issue is invisible to normal users.'))
                    h.flash_success(' '.join(msgs))
                else:
                    h.flash_success(_('Issue reported to an administrator'))
            except toolkit.ValidationError:
                toolkit.abort(404)
            except toolkit.ObjectNotFound:
                toolkit.abort(404)
            except ReportAlreadyExists, e:
                h.flash_error(e.message)

            p.toolkit.redirect_to('issues_show',
                                  dataset_id=dataset_id,
                                  issue_number=issue_number)

    def report_comment(self, dataset_id, issue_number, comment_id):
        dataset = self._before_dataset(dataset_id)
        if request.method == 'POST':
            if not c.user:
                msg = _('You must be logged in to report comments')
                toolkit.abort(401, msg)
            try:
                report_info = toolkit.get_action('issue_comment_report')(
                    data_dict={
                        'comment_id': comment_id,
                        'issue_number': issue_number,
                        'dataset_id': dataset_id
                    }
                )
                if report_info:
                    # we have this info if it is an admin
                    msgs = [_('Report acknowledged.')]
                    if report_info['abuse_status'] == \
                            issuemodel.AbuseStatus.abuse.value:
                        msgs.append(_('Marked as abuse/spam.'))
                    msgs.append(_('Comment is visible.')
                                if report_info['visibility'] == 'visible' else
                                _('Comment is invisible to normal users.'))
                    h.flash_success(' '.join(msgs))
                else:
                    h.flash_success(_('Comment has been reported to an administrator'))
                p.toolkit.redirect_to('issues_show',
                                      dataset_id=dataset_id,
                                      issue_number=issue_number)
            except toolkit.ValidationError:
                toolkit.abort(404)
            except toolkit.ObjectNotFound:
                toolkit.abort(404)
            except ReportAlreadyExists, e:
                h.flash_error(e.message)
            p.toolkit.redirect_to('issues_show', dataset_id=dataset_id,
                                  issue_number=issue_number)

    def report_clear(self, dataset_id, issue_number):
        dataset = self._before_dataset(dataset_id)
        if request.method == 'POST':
            try:
                toolkit.get_action('issue_report_clear')(
                    data_dict={
                        'issue_number': issue_number,
                        'dataset_id': dataset_id
                    }
                )
                h.flash_success(_('Issue report cleared'))
                p.toolkit.redirect_to('issues_show',
                                      dataset_id=dataset_id,
                                      issue_number=issue_number)
            except toolkit.NotAuthorized:
                msg = _(u'You must be logged in clear abuse reports')
                toolkit.abort(401, msg)
            except toolkit.ValidationError:
                toolkit.abort(404)
            except toolkit.ObjectNotFound:
                toolkit.abort(404)

    def comment_report_clear(self, dataset_id, issue_number, comment_id):
        dataset = self._before_dataset(dataset_id)
        if request.method == 'POST':
            try:
                toolkit.get_action('issue_comment_report_clear')(
                    data_dict={'comment_id': comment_id,
                               'issue_number': issue_number,
                               'dataset_id': dataset_id}
                )
                h.flash_success(_('Spam/abuse report cleared'))
                p.toolkit.redirect_to('issues_show',
                                      dataset_id=dataset_id,
                                      issue_number=issue_number)
            except toolkit.NotAuthorized:
                msg = _(u'You must be logged in to clear abuse reports')
                toolkit.abort(401, msg)
            except toolkit.ValidationError:
                toolkit.abort(404)
            except toolkit.ObjectNotFound:
                toolkit.abort(404)

    def issues_for_organization(self, org_id):
        """
        Display a page containing a list of all issues for a given organization
        """
        self._before_org(org_id)
        try:
            template_params = issues_for_org(org_id, request.GET)
        except toolkit.ValidationError, e:
            msg = toolkit._(u'Validation error: {0}').format(e.error_summary)
            log.warning(msg + u' - Issues for org: %s', org_id)
            h.flash(msg, category='alert-error')
            return p.toolkit.redirect_to('issues_for_organization',
                                         org_id=org_id)
        return render("issues/organization_issues.html",
                      extra_vars=template_params)

        # TO DELETE
        c.org = model.Group.get(org_id)

        q = """
            SELECT table_id
            FROM member
            WHERE group_id='{gid}'
              AND table_name='package'
              AND state='active'
        """.format(gid=c.org.id)
        results = model.Session.execute(q)

        dataset_ids = [x['table_id'] for x in results]
        issues = model.Session.query(issuemodel.Issue)\
            .filter(issuemodel.Issue.dataset_id.in_(dataset_ids))\
            .order_by(issuemodel.Issue.created.desc())

        c.results = collections.defaultdict(list)
        for issue in issues:
            c.results[issue.package].append(issue)
        c.package_set = sorted(set(c.results.keys()), key=lambda x: x.title)
        return render("issues/organization_issues.html")

    def all_issues_page(self):
        """
        Display a page containing a list of all issues items
        """
        template_params = all_issues(request.GET)
        return render("issues/all_issues.html", extra_vars=template_params)


def _dataset_handle_error(dataset_id, exc):
    msg = toolkit._(u'Validation error: {0}').format(exc.error_summary)
    h.flash(msg, category='alert-error')
    return p.toolkit.redirect_to('issues_dataset', dataset_id=dataset_id)


def issues_for_dataset(dataset_id, get_query_dict):
    query, errors = toolkit.navl_validate(
        dict(get_query_dict),
        schema.issue_dataset_controller_schema()
    )
    if errors:
        raise toolkit.ValidationError(errors)
    query.pop('__extras', None)
    return _search_issues(dataset_id=dataset_id, **query)


def issues_for_org(org_id, get_query_dict):
    query, errors = toolkit.navl_validate(
        dict(get_query_dict),
        schema.issue_dataset_controller_schema()
    )
    if errors:
        raise toolkit.ValidationError(errors)
    query.pop('__extras', None)
    template_params = _search_issues(organization_id=org_id,
                                     include_datasets=True,
                                     **query)
    template_params['org'] = \
        logic.get_action('organization_show')({}, {'id': org_id})
    return template_params

def all_issues(get_query_dict):
    query, errors = toolkit.navl_validate(
        dict(get_query_dict),
        schema.issue_dataset_controller_schema()
    )
    if errors:
        raise toolkit.ValidationError(errors)
    query.pop('__extras', None)
    return _search_issues(include_datasets=True,
                          **query)

def _search_issues(dataset_id=None,
                   organization_id=None,
                   status=issuemodel.ISSUE_STATUS.open,
                   sort='newest',
                   visibility=None,
                   abuse_status=None,
                   q='',
                   page=1,
                   per_page=get_issues_per_page()[0],
                   include_datasets=False,
                   include_reports=True):
    # use the function params to set default for our arguments to our
    # data_dict if needed
    params = locals().copy()

    # convert per_page, page parameters to api limit/offset
    limit = per_page
    offset = (page - 1) * limit
    params.pop('page', None)
    params.pop('per_page', None)

    # fetch only the results for the current page
    params.update({
        'include_count': False,
        'limit': limit,
        'offset': offset,
    })

    results_for_current_page = toolkit.get_action('issue_search')(
        data_dict=params
    )
    issues = results_for_current_page['results']

    # fetch the total count of all the search results without dictizing
    params['include_count'] = True
    params['include_results'] = False
    params.pop('limit', None)
    params.pop('offset', None)
    all_search_results = toolkit.get_action('issue_search')(data_dict=params)
    issue_count = all_search_results['count']

    pagination = Pagination(page, limit, issue_count)

    template_variables = {
        'issues': issues,
        'status': status,
        'sort': sort,
        'q': q,
        'pagination': pagination,
    }
    if visibility:
        template_variables['visibility'] = visibility
    return template_variables
