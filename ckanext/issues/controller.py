"""
CKAN Issues Extension
"""
from logging import getLogger
log = getLogger(__name__)

from sqlalchemy import func
from pylons.i18n import _
from pylons.decorators import jsonify
from pylons import request, tmpl_context as c
from ckan.lib.base import BaseController, response, render, abort
from ckan.lib.search import query_for
from ckanext.issues import model
import re

AUTOCOMPLETE_LIMIT = 10
VALID_CATEGORY = re.compile(r"[0-9a-z\-\._]+")

def get_user_id(user_name):
    """
    Return the ID of user_name, or None if no such user ID exists
    """
    query = model.Session.query(model.User)\
        .filter(model.User.name == user_name)
    return query.first().id if query.first() else None

def get_user_full_name(user_id):
    """
    Return the user name of user_id, or None if no such user exists
    """
    query = model.Session.query(model.User)\
        .filter(model.User.id == user_id)
    return query.first().display_name if query.first() else None

class IssueController(BaseController):
    """
    The CKANEXT-Issues Controller.
    """
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
                 'creator': get_user_full_name(issues.creator),
                 'created': issues.created.strftime('%d %h %Y')}
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
        issues = model.Issue.get(issue_id)
        if not issues:
            response.status_int = 400
            return {'error': "Invalid issues ID"}

        # check for a resolver
        resolver = request.params.get('resolver')
        if not resolver:
            response.status_int = 400
            return {'error': "No resolver given"}

        # check that resolver matches the current user
        current_user = model.User.get(request.environ.get('REMOTE_USER'))
        if not current_user:
            response.status_int = 403
            return {'error': "You are not authorized to make this request"}
        if not resolver == current_user.id:
            response.status_int = 403
            return {'error': "You are not authorized to make this request"}

        # update database
        session = model.meta.Session()
        try:
            issues.resolved = model.datetime.now()
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

    def issue_page(self):
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
                .filter(model.Issue.issue_category_id == t.issue_category_id)\
                .order_by(model.Issue.created.desc())
            for issues in tc.issues:
                # get the package name for each package if one exists
                if issues.package_id:
                    c.pkg_names[issues.package_id] = model.Package.get(issues.package_id).name
            c.categories.append(tc)
        # sort into alphabetical order
        c.categories.sort(key = lambda x: x.name)
        return render("issues.html")
