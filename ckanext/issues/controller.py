"""
CKAN Issues Extension
"""
import collections
from logging import getLogger
log = getLogger(__name__)

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from pylons.i18n import _
from pylons.decorators import jsonify
from pylons import request, config, tmpl_context as c
from ckan.lib.base import BaseController, response, render, abort, redirect
from ckan.lib.search import query_for
import ckan.lib.helpers as h
from ckanext.issues import model
import re

AUTOCOMPLETE_LIMIT = 10
VALID_CATEGORY = re.compile(r"[0-9a-z\-\._]+")

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
    from_address = config.get('ckanext.issues.from_address', 'admin@localhost.local')

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
        'issue' : issue,
        'username': issue.reporter.fullname or issue.reporter.name,
        'site_url'   : h.url_for(controller='ckanext.issues.controller:IssueController',
                         action='issue_page', package_id=issue.package.name, qualified=True)
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
    except Exception, e:
        log.error('Failed to send an email message for issue notification')



class IssueAPIController(BaseController):

    @jsonify
    def get(self):
        """
        Return a list of issues items, sorted with the most recently created items
        first.

        The list can be limited by specifying the following parameters:
        * package: a package ID or name
        * category: a category ID or name
        * resolved: 0 or 1, where 0 is not resolved and 1 is resolved
        * limit: a positive integer, sets the maximum number of items to be returned.
        """
        query = model.Session.query(model.Issue).order_by(model.Issue.created.desc())

        # check for a package ID or name in the request
        package_id = request.params.get('package')
        if package_id:
            # if a package was specified, make sure that it is
            # a valid package ID/name
            package =  model.Package.get(package_id)
            if not package:
                response.status_int = 404
                return {'error': "Package not found"}
            query = query.filter(model.Issue.package_id == package.id)

        # check for a category
        category_name_or_id = request.params.get('category')
        if category_name_or_id:
            category = model.IssueCategory.get(category_name_or_id)
            if not category:
                response.status_int = 404
                return {'error': "Category not found"}
            query = query.filter(model.Issue.issue_category_id == category.id)

        # check for resolved status
        resolved = request.params.get('resolved')
        if resolved:
            try:
                resolved = int(resolved)
            except:
                response.status_int = 400
                return {'error': "Resolved can only be 0 or 1"}
            if not ((resolved == 0) or (resolved == 1)):
                response.status_int = 400
                return {'error': "Resolved can only be 0 or 1"}
            if resolved:
                query = query.filter(model.Issue.resolved != None)
            else:
                query = query.filter(model.Issue.resolved == None)

        # check for a query limit
        limit = request.params.get('limit')
        if limit:
            try:
                limit = int(limit)
            except:
                response.status_int = 400
                return {'error': "Limit value is not a positive integer"}
            if not limit > 0:
                response.status_int = 400
                return {'error': "Limit value is not a positive integer"}
            query = query.limit(limit)

        return [{'id': issues.id,
                 'category': model.IssueCategory.get(issues.issue_category_id).name,
                 'description': issues.description,
                 'creator': issues.reporter.name,
                 'created': issues.created.strftime('%d %h %Y'),
                 'package': issues.package.name if issues.package else "",
                 "resolved_by": issues.resolver or "",
                 "resolved_date": issues.resolved.strftime('%d %h %Y') if issues.resolved else "",
                 "resource": issues.resource.id if issues.resource else ""}
                for issues in query if query]

    @jsonify
    def post(self):
        """
        Add a new issues item.

        Issue items must have a category, description and a creator. Other fields
        are optional.
        """
        # check for a category name
        category_name = request.params.get('category_name')
        if not category_name:
            response.status_int = 400
            return {'msg': "Please enter a category"}

        # make sure category name consists of valid characters
        category_name = category_name.strip()
        valid = VALID_CATEGORY.match(category_name)
        if not valid or not valid.end() == len(category_name):
            response.status_int = 400
            return {'msg': "Category can only consist of lowercase " +
                           "characters, numbers and the symbols .-_"}

        # check for a description
        description = request.params.get('description')
        if not description:
            response.status_int = 400
            return {'msg': "Please enter a description"}

        # check for a creator
        creator = request.params.get('creator')
        if not creator:
            response.status_int = 400
            return {'msg': "Please enter a creator for this issues item"}

        # check that creator matches the current user
        current_user = model.User.get(request.environ.get('REMOTE_USER'))
        if not current_user:
            response.status_int = 403
            return {'msg': "You are not authorized to make this request"}
        if not creator == current_user.id:
            response.status_int = 403
            return {'msg': "You are not authorized to make this request"}

        # check for a package ID or name in the request
        package_name = request.params.get('package_name')
        if package_name:
            # if a package was specified, make sure that it is
            # a valid package ID/name
            package =  model.Package.get(package_name)
            if not package:
                response.status_int = 400
                return {'msg': "Invalid package name or ID"}

        session = model.meta.Session()

        # if category doesn't already exist, create it
        category = model.IssueCategory.get(category_name)
        if not category:
            try:
                category = model.IssueCategory(unicode(category_name))
                session.add(category)
                session.commit()
            except Exception as e:
                log.warn("Database Error: " + str(e))
                session.rollback()
                response.status_int = 500
                return {'msg': "Could not add category to database."}

        # add new item to database
        try:
            t = model.Issue(category.id, description, creator)
            t.package_id = package.id if package else None
            session.add(t)
            session.commit()
        except Exception as e:
            log.warn("Database Error: " + str(e))
            session.rollback()
            response.status_int = 500
            return {'msg': "Could not add issues item to database"}

        return {}

    @jsonify
    def resolve(self):
        """
        Resolve a issues item.
        """
        # check for a issues ID
        issue_id = request.params.get('issue_id')
        if not issue_id:
            response.status_int = 400
            return {'error': "No issues ID given"}

        # make sure issues ID is valid
        issue = model.Issue.get(issue_id)
        if not issue:
            response.status_int = 400
            return {'error': "Invalid issues ID"}

        # check for a resolver
        resolver = request.params.get('resolver')
        if not resolver:
            response.status_int = 400
            return {'error': "No resolver given"}

        resolver = model.Session.query(model.User).filter(model.User.name==resolver).first()

        # check that resolver 'owns' the package
        if not h.check_access('package_update', {'id':issue.package.id}):
            response.status_int = 403
            return {'error': "You are not authorized to make this request"}

        # update database
        session = model.meta.Session()
        try:
            issue.resolved = model.datetime.now()
            issue.resolver = resolver.id
            session.commit()
        except Exception as e:
            log.warn("Database Error: " + str(e))
            session.rollback()
            response.status_int = 500
            return {'error': "Could not add issues item to database"}

        return {}

    @jsonify
    def category(self):
        """
        Return a list of issues all issues categories.
        """
        query = model.Session.query(model.IssueCategory)
        return [{'name': category.name} for category in query if query]

    @jsonify
    def autocomplete(self):
        """
        Issue autocomplete API
        """
        # Get the "term" (what the user has typed so far in the input box) from
        # jQuery UI
        term = request.params.get("term")

        if term:
            # Make a list of categories that match the term and return it
            query = model.IssueCategory.search(term)
            category_names = [cat.name for cat in query]
            return category_names[:AUTOCOMPLETE_LIMIT]
        else:
            # No categories match what the user has typed.
            return []

class IssueController(BaseController):
    """
    The CKANEXT-Issues Controller.
    """

    def add(self, package_id, resource_id=None):
        if not c.user:
            abort(401, "Please login to add a new issue")

        c.pkg = model.Package.get(package_id)
        c.pkg_dict = c.pkg.as_dict()

        resource = model.Resource.get(resource_id) if resource_id else None
        c.resource_name = resource.name or resource.description if resource else ""

        c.categories = [ {'text': cat.description, 'value': cat.id } for cat in
                model.Session.query(model.IssueCategory)
                    .order_by('description').all()
                ]
        # 3 is id of other category
        c.errors, c.error_summary = {}, {}
        c.category = "3"

        if request.method == 'POST':
            c.category = request.POST.get('category')
            c.title = request.POST.get('title')
            c.description = request.POST.get('description')

            if not c.title:
                c.error_summary['title'] = ["Please enter a title"]
            if not c.description:
                c.error_summary['description'] = ["Please provide a description of the issue"]
            if not c.category:
                c.error_summary['category'] = ["Please choose a category"]
            c.errors = c.error_summary

            # Do we have a resource?

            if not c.error_summary:
                user = model.User.get(c.user)
                issue = model.Issue(category_id=c.category,
                                description=c.description,
                                creator=user.id)
                issue.package_id = c.pkg.id
                if c.resource_name:
                    issue.resource_id = resource.id
                model.Session.add(issue)
                model.Session.commit()

                _notify(issue)

                h.flash_success("Your issue has been registered, thank you for the feedback")
                redirect(h.url_for('issue_page', package_id=c.pkg.name))

        return render("issues/add_issue.html")

    def issue_page(self, package_id):
        """
        Display a page containing a list of all issues items, sorted by category.
        """
        # categories
        c.pkg = model.Package.get(package_id)
        c.pkg_dict = c.pkg.as_dict()
        c.issues = model.Session.query(model.Issue)\
            .filter(model.Issue.package_id==c.pkg.id)\
            .options(joinedload(model.Issue.comments))\
            .order_by(model.Issue.created.desc())
        c.resource_id = request.GET.get('resource', "")
        return render("issues/issues.html")

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
