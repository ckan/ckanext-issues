import collections
from logging import getLogger
import re

from sqlalchemy import func
from pylons.i18n import _
from pylons import request, config, tmpl_context as c

from ckan.lib.base import BaseController, render, abort, redirect
import ckan.lib.helpers as h
import ckan.model as model
import ckan.logic as logic
import ckan.plugins as p
from ckan.plugins import toolkit

import ckanext.issues.model as issuemodel
from ckanext.issues.controller import show
from ckanext.issues.exception import ReportAlreadyExists
from ckanext.issues.lib import helpers as issues_helpers
from ckanext.issues.logic import schema
from ckanext.issues.lib.helpers import Pagination, get_issues_per_page

log = getLogger(__name__)

AUTOCOMPLETE_LIMIT = 10
VALID_CATEGORY = re.compile(r"[0-9a-z\-\._]+")
ISSUES_PER_PAGE = (15, 30, 50)


def _notify(issue):
    # Depending on configuration, and availability of data we
    # should email the admin and the organization
    notify_admin = config.get("ckanext.issues.notify_admin", False)
    notify_owner = config.get("ckanext.issues.notify_owner", False)
    if not notify_admin and not notify_owner:
        return

    from ckan.lib.mailer import mail_recipient
    from genshi.template.text import NewTextTemplate

    admin_address = config.get('email_to')
    # from_address = config.get('ckanext.issues.from_address',
    #  'admin@localhost.local')

    org = issue.package.owner_org
    if 'contact-address' in issue.package.extras:
        contact_name = issue.package.extras.get('contact-name')
        contact_address = issue.package.extras.get('contact-email')
    else:
        contact_name = org.extras.get('contact-name', 'Publisher')
        contact_address = org.extras.get('contact-email')

    # Send to admin if no contact address, and only cc admin if
    # they are not also in the TO field.
    to_address = contact_address or admin_address
    cc_address = admin_address if contact_address else None

    extra_vars = {
        'issue': issue,
        'username': issue.reporter.fullname or issue.reporter.name,
        'site_url': h.url_for(
            controller='ckanext.issues.controller:IssueController',
            action='issue_page',
            package_id=issue.package.name,
            qualified=True
        )
    }

    email_msg = render("issues/email/new_issue.txt", extra_vars=extra_vars,
                       loader_class=NewTextTemplate)

    headers = {}
    if cc_address:
        headers['CC'] = cc_address

    try:
        if not contact_name:
            contact_name = org.title

        mail_recipient(contact_name, to_address,
                       "Dataset issue",
                       email_msg, headers=headers)
    except Exception:
        log.error('Failed to send an email message for issue notification')


class IssueController(BaseController):
    def _before(self, package_id):
        self.context = {'for_view': True}
        try:
            pkg = logic.get_action('package_show')(self.context, {'id':
                                                   package_id})
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

    def new(self, package_id, resource_id=None):
        self._before(package_id)
        if not c.user:
            abort(401, _('Please login to add a new issue'))

        data_dict = {
            'dataset_id': c.pkg['id'],
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
                c.error_summary['title'] = ["Please enter a title"]
            c.errors = c.error_summary

            if not c.error_summary:  # save and redirect
                issue_dict = logic.get_action('issue_create')(
                    data_dict=data_dict
                )
                h.flash_success(_('Your issue has been registered, '
                                  'thank you for the feedback'))
                redirect(h.url_for(
                    'issues_show',
                    package_id=c.pkg['name'],
                    id=issue_dict['id']
                    ))

        c.data_dict = data_dict
        return render("issues/add.html")

    def show(self, id, package_id):
        dataset = self._before(package_id)
        try:
            extra_vars = show.show(id, package_id, session=model.Session)
        except toolkit.ValidationError, e:
            p.toolkit.abort(
                404, toolkit._('Issue not found: {0}'.format(e.error_summary)))
        extra_vars['dataset'] = dataset
        return p.toolkit.render('issues/show.html', extra_vars=extra_vars)

    def edit(self, id, package_id):
        self._before(package_id)
        issue = p.toolkit.get_action('issue_show')(data_dict={'id': id})
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
            data_dict['id'] = id
            data_dict['dataset_id'] = package_id
            try:
                p.toolkit.get_action('issue_update')(data_dict=data_dict)
                return p.toolkit.redirect_to('issues_show', id=id,
                                             package_id=package_id)
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

    def comments(self, id, package_id):
        # POST only
        if request.method != 'POST':
            abort(500, _('Invalid request'))

        self._before(package_id)

        auth_dict = {
            'dataset_id': c.pkg['id'],
            'id': id
            }
        # Are we not repeating stuff in logic ???
        try:
            logic.check_access('issue_create', self.context, auth_dict)
        except logic.NotAuthorized:
            abort(401, _('Not authorized'))

        next_url = h.url_for(
            'issues_show',
            package_id=c.pkg['name'],
            id=id
            )
        # TODO: (?) move validation somewhere better than controller
        comment = request.POST.get('comment')
        if not comment or comment.strip() == '':
            h.flash_error(_('Comment cannot be empty'))
            redirect(next_url)
            return

        # do this first because will error here if not allowed and do not want
        # comment created in that case
        if 'close' in request.POST or 'reopen' in request.POST:
            status = (issuemodel.ISSUE_STATUS.closed if 'close' in request.POST
                      else issuemodel.ISSUE_STATUS.open)
            issue_dict = {
                'id': id,
                'dataset_id': package_id,
                'status': status
                }
            logic.get_action('issue_update')(self.context, issue_dict)
            if 'close' in request.POST:
                h.flash_success(_("Issue closed"))
            else:
                h.flash_success(_("Issue re-opened"))

        data_dict = {
            'issue_id': id,
            'author_id': c.userobj.id,
            'comment': comment.strip()
            }
        logic.get_action('issue_comment_create')(self.context, data_dict)

        redirect(next_url)

    def dataset(self, package_id):
        """
        Display a page containing a list of all issues items for a dataset,
        sorted by category.
        """
        self._before(package_id)
        try:
            extra_vars = issues_for_dataset(package_id, request.GET)
        except toolkit.ValidationError, e:
            _dataset_handle_error(package_id, e)
        return render("issues/dataset.html", extra_vars=extra_vars)

    def delete(self, dataset_id, issue_id):
        dataset = self._before(dataset_id)
        if 'cancel' in request.params:
            h.redirect_to('issues_show', package_id=dataset_id, id=issue_id)

        if request.method == 'POST':
            try:
                toolkit.get_action('issue_delete')(
                    data_dict={'issue_id': issue_id, 'dataset_id': dataset_id})
            except toolkit.NotAuthorized:
                msg = _('Unauthorized to delete issue {0}'.format(issue_id))
                toolkit.abort(401, msg)

            h.flash_notice(_('Issue {0} has been deleted.'.format(issue_id)))
            h.redirect_to('issues_dataset', package_id=dataset_id)
        else:
            return render('issues/confirm_delete.html',
                          extra_vars={
                              'issue_id': issue_id,
                              'pkg': dataset,
                          })

    def assign(self, dataset_id, issue_id):
        dataset = self._before(dataset_id)
        if request.method == 'POST':
            try:
                assignee_id = request.POST.get('assignee')
                assignee = toolkit.get_action('user_show')(
                    data_dict={'id': assignee_id})
            except toolkit.ObjectNotFound:
                h.flash_error(_('User {0} does not exist'.format(assignee_id)))
                return p.toolkit.redirect_to('issues_show',
                                             id=issue_id,
                                             package_id=dataset_id)

            try:
                toolkit.get_action('issue_update')(
                    data_dict={'id': issue_id, 'assignee_id': assignee['id'],
                               'dataset_id': dataset_id})
            except toolkit.NotAuthorized:
                msg = _('Unauthorized to assign users to issue'.format(
                    issue_id))
                toolkit.abort(401, msg)
            except toolkit.ValidationError, e:
                toolkit.abort(404)


        return p.toolkit.redirect_to('issues_show',
                                     id=issue_id,
                                     package_id=dataset_id)

    def report(self, dataset_id, issue_id):
        dataset = self._before(dataset_id)
        if request.method == 'POST':
            if not c.user:
                msg = _('You must be logged in to report issues'.format(
                    issue_id))
                toolkit.abort(401, msg)
            try:
                toolkit.get_action('issue_report')(
                    data_dict={'issue_id': issue_id, 'dataset_id': dataset_id}
                )
                h.flash_success(_('Issue reported to an administrator'))
            except toolkit.ValidationError:
                toolkit.abort(404)
            except ReportAlreadyExists, e:
                h.flash_error(e.message)
            h.redirect_to('issues_show', package_id=dataset_id,
                          id=issue_id)

    def report_comment(self, dataset_id, issue_id, comment_id):
        dataset = self._before(dataset_id)
        if request.method == 'POST':
            if not c.user:
                msg = _('You must be logged in to report comments')\
                    .format(issue_id)
                toolkit.abort(401, msg)
            try:
                toolkit.get_action('issue_comment_report')(
                    data_dict={'issue_comment_id': comment_id,
                               'dataset_id': dataset_id}
                )
                h.flash_success(
                    _('Comment has been reported to an administrator')
                )
                h.redirect_to('issues_show', package_id=dataset_id,
                              id=issue_id)
            except toolkit.ValidationError:
                toolkit.abort(404)
            except ReportAlreadyExists, e:
                h.flash_error(e.message)
            h.redirect_to('issues_show', package_id=dataset_id,
                          id=issue_id)

    def report_clear(self, dataset_id, issue_id):
        dataset = self._before(dataset_id)
        if request.method == 'POST':
            try:
                toolkit.get_action('issue_report_clear')(
                    data_dict={'issue_id': issue_id, 'dataset_id': dataset_id}
                )
                h.flash_success(_('Issue report cleared'))
                h.redirect_to('issues_show', package_id=dataset_id,
                              id=issue_id)
            except toolkit.NotAuthorized:
                msg = _('You must be logged in clear abuse reports')\
                    .format(issue_id)
                toolkit.abort(401, msg)
            except toolkit.ValidationError:
                toolkit.abort(404)

    def comment_report_clear(self, dataset_id, issue_id, comment_id):
        dataset = self._before(dataset_id)
        if request.method == 'POST':
            try:
                toolkit.get_action('issue_comment_report_clear')(
                    data_dict={'issue_comment_id': comment_id,
                               'dataset_id': dataset_id}
                )
                h.flash_success(_('Abuse report cleared'))
                h.redirect_to('issues_show', package_id=dataset_id,
                              id=issue_id)
            except toolkit.NotAuthorized:
                msg = _('You must be logged in to clear abuse reports')\
                    .format(issue_id)
                toolkit.abort(401, msg)
            except toolkit.ValidationError:
                toolkit.abort(404)

    def issues_for_organization(self, org_id):
        """
        Display a page containing a list of all issues for a given organization
        """
        try:
            template_params = issues_for_org(org_id, request.GET)
        except toolkit.ValidationError, e:
            msg = toolkit._("Validation error: {0}".format(e.error_summary))
            log.warning(msg + ' - Issues for org: %s', org_id)
            h.flash(msg, category='alert-error')
            return p.toolkit.redirect_to('issues_for_organization', org_id=org_id)
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

        package_ids = [x['table_id'] for x in results]
        issues = model.Session.query(issuemodel.Issue)\
            .filter(issuemodel.Issue.dataset_id.in_(package_ids))\
            .order_by(issuemodel.Issue.created.desc())

        c.results = collections.defaultdict(list)
        for issue in issues:
            c.results[issue.package].append(issue)
        c.package_set = sorted(set(c.results.keys()), key=lambda x: x.title)
        return render("issues/organization_issues.html")

    def all_issues_page(self):
        """
        Display a page containing a list of all issues items, sorted by
        category.

        NB This doesn't seem to work - no connection between issues and
        categories in the model
        """
        # categories
        categories = model.Session.query(
            func.count(issuemodel.Issue.id).label('issue_count'),
            issuemodel.Issue.issue_category_id)\
            .filter(issuemodel.Issue.resolved == None)\
            .group_by(issuemodel.Issue.issue_category_id)

        c.categories = []
        c.pkg_names = {}
        for t in categories:
            tc = issuemodel.IssueCategory.get(t.issue_category_id)
            tc.issue_count = t.issue_count

            # get issues items for each category
            tc.issues = model.Session.query(issuemodel.Issue).filter(issuemodel.Issue.resolved == None)\
                .filter(issuemodel.Issue.issue_category_id == t.issue_category_id) \
                .order_by(issuemodel.Issue.created.desc())

            for issues in tc.issues:
                if issues.package_id:
                    c.pkg_names[issues.package_id] = model.Package.get(issues.package_id).name
            c.categories.append(tc)
        # sort into alphabetical order
        c.categories.sort(key = lambda x: x.name)
        return render("issues/all_issues.html")


def _dataset_handle_error(package_id, exc):
    msg = toolkit._("Validation error: {0}".format(exc.error_summary))
    h.flash(msg, category='alert-error')
    return p.toolkit.redirect_to('issues_dataset', package_id=package_id)


def issues_for_dataset(dataset_id, get_query_dict):
    query, errors = toolkit.navl_validate(
        dict(get_query_dict),
        schema.issue_dataset_controller_schema()
    )
    if errors:
        raise toolkit.ValidationError(errors).error_summary
    query.pop('__extras', None)

    return _search_issues(dataset_id=dataset_id, **query)


def issues_for_org(org_id, get_query_dict):
    query, errors = toolkit.navl_validate(
        dict(get_query_dict),
        schema.issue_dataset_controller_schema()
    )
    if errors:
        raise toolkit.ValidationError(errors).error_summary
    query.pop('__extras', None)

    template_params = _search_issues(organization_id=org_id,
                                     include_datasets=True,
                                     **query)
    template_params['org'] = \
        logic.get_action('organization_show')({}, {'id': org_id})
    return template_params


def _search_issues(dataset_id=None, organization_id=None,
                   status=issuemodel.ISSUE_STATUS.open,
                   sort='newest', spam_state=None, q='', page=1,
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
    params['offset'] = offset

    search_result = toolkit.get_action('issue_search')(data_dict=params)
    issues = search_result['results']
    issue_count = search_result['count']

    pagination = Pagination(page, limit, issue_count)

    template_variables = {
        'issues': issues,
        'status': status,
        'sort': sort,
        'q': q,
        'pagination': pagination,
    }
    if spam_state:
        template_variables['spam_state'] = spam_state
    return template_variables
