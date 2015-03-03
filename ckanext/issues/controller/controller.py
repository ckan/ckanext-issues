"""
CKAN Issues Extension
"""
import collections
from logging import getLogger
import re

from sqlalchemy import func
from pylons.i18n import _
from pylons import request, config, tmpl_context as c
import webhelpers.date

from ckan.lib.base import BaseController, render, abort, redirect
import ckan.lib.helpers as h
import ckan.model as model
import ckan.logic as logic
import ckan.plugins as p
from ckan.plugins import toolkit

import ckanext.issues.model as issuemodel
from ckanext.issues.controller import home


log = getLogger(__name__)

AUTOCOMPLETE_LIMIT = 10
VALID_CATEGORY = re.compile(r"[0-9a-z\-\._]+")
ISSUES_PER_PAGE = (15, 30, 50)


def _notify(issue):
    # Depending on configuration, and availability of data we
    # should email the admin and the publisher/
    notify_admin = config.get("ckanext.issues.notify_admin", False)
    notify_owner = config.get("ckanext.issues.notify_owner", False)
    if not notify_admin and not notify_owner:
        return

    from ckan.lib.mailer import mail_recipient
    from genshi.template.text import NewTextTemplate

    admin_address = config.get('email_to')
    # from_address = config.get('ckanext.issues.from_address',
    #  'admin@localhost.local')

    publisher = issue.package.get_groups('publisher')[0]
    if 'contact-address' in issue.package.extras:
        contact_name = issue.package.extras.get('contact-name')
        contact_address = issue.package.extras.get('contact-email')
    else:
        contact_name = publisher.extras.get('contact-name', 'Publisher')
        contact_address = publisher.extras.get('contact-email')

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
            contact_name = publisher.title

        mail_recipient(contact_name, to_address,
                       "Dataset issue",
                       email_msg, headers=headers)
    except Exception:
        log.error('Failed to send an email message for issue notification')


class IssueController(BaseController):
    def _before(self, package_id):
        self.context = {'for_view': True}
        try:
            c.pkg = logic.get_action('package_show')(self.context, {'id':
                                                     package_id})
            # need this as some templates in core explicitly reference
            # c.pkg_dict
            c.pkg_dict = c.pkg
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
        self._before(package_id)
        data_dict = {
            'id': id
        }
        c.issue = logic.get_action('issue_show')(data_dict=data_dict)
        # annoying we repeat what logic has done but easiest way to get proper
        # datetime ...
        issueobj = issuemodel.Issue.get(id)

        c.issue['comment'] = c.issue['description'] or _('No description provided')
        c.issue['time_ago'] = webhelpers.date.time_ago_in_words(issueobj.created,
                granularity='minute')
        c.comment_count = len(issueobj.comments)
        for idx, comment in enumerate(c.issue['comments']):
            commentobj = issueobj.comments[idx]
            comment['time_ago'] = webhelpers.date.time_ago_in_words(
                commentobj.created,
                granularity='minute'
                )
        # can they administer the issue (update, close etc)
        c.issue_admin = False
        if c.userobj:
            c.current_user = issuemodel._user_dict(c.userobj)
            try:
                p.toolkit.check_access(
                    'issue_update',
                    context=self.context,
                    data_dict={
                    'id': id,
                    'dataset_id': package_id
                    })
                c.issue_admin = True
            except logic.NotAuthorized:
                pass

        return render('issues/show.html')

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

    def home(self, package_id):
        """
        Display a page containing a list of all issues items, sorted by category.
        """
        self._before(package_id)
        try:
            extra_vars = home.home(package_id, request.GET)
        except toolkit.ValidationError, e:
            _home_handle_error(e)
        return render("issues/home.html", extra_vars=extra_vars)

    def publisher_issue_page(self, publisher_id):
        """
        Display a page containing a list of all issues items for a given
        publisher
        """
        c.publisher = model.Group.get(publisher_id)

        q = """
            SELECT table_id
            FROM member
            WHERE group_id='{gid}'
              AND table_name='package'
              AND state='active'
        """.format(gid=c.publisher.id)
        results = model.Session.execute(q)

        package_ids = [x['table_id'] for x in results]
        issues = model.Session.query(model.Issue)\
            .filter(model.Issue.package_id.in_(package_ids))\
            .order_by(model.Issue.created.desc())

        c.results = collections.defaultdict(list)
        for issue in issues:
            c.results[issue.package].append(issue)
        c.package_set = sorted(set(c.results.keys()), key=lambda x: x.title)
        return render("issues/publisher_issues.html")

    def all_issues_page(self):
        """
        Display a page containing a list of all issues items, sorted by category.
        """
        # categories
        categories = model.Session.query(func.count(model.Issue.id).label('issue_count'),
                                         model.Issue.issue_category_id)\
            .filter(model.Issue.resolved == None)\
            .group_by(model.Issue.issue_category_id)

        c.categories = []
        c.pkg_names = {}
        for t in categories:
            tc = model.IssueCategory.get(t.issue_category_id)
            tc.issue_count = t.issue_count

            # get issues items for each category
            tc.issues = model.Session.query(model.Issue).filter(model.Issue.resolved == None)\
                .filter(model.Issue.issue_category_id == t.issue_category_id) \
                .order_by(model.Issue.created.desc())

            for issues in tc.issues:
                if issues.package_id:
                    c.pkg_names[issues.package_id] = model.Package.get(issues.package_id).name
            c.categories.append(tc)
        # sort into alphabetical order
        c.categories.sort(key = lambda x: x.name)
        return render("issues/all_issues.html")


def _home_handle_error(package_id, exc):
    msg = toolkit._("Validation error: {0}".format(exc.error_summary))
    h.flash(msg, category='alert-error')
    return p.toolkit.redirect_to('issues_home', package_id=package_id)
