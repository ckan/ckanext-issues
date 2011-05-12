"""
CKAN Todo Extension
"""
from logging import getLogger
log = getLogger(__name__)

from pylons.i18n import _
from pylons.decorators import jsonify
from pylons import request, tmpl_context as c
from ckan.lib.base import BaseController, response, render, abort
from ckanext.todo import model

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
    return query.first().fullname if query.first() else None

def get_category_name(category_id):
    """
    Return the category name of category_id, or None if no such category exists
    """
    query = model.Session.query(model.TodoCategory)\
        .filter(model.TodoCategory.id == category_id)
    return query.first().name if query.first() else None

class TodoController(BaseController):
    """
    The CKANEXT-Todo Controller.
    """
    @jsonify
    def get(self):
        """
        Return a list of todo items, sorted with the most recently created items
        first.

        The list can be limited by specifying the following parameters:
        * package: a package ID or name
        * (NOT YET IMPLEMENTED) category: a category ID or name 
        * (NOT YET IMPLEMENTED) resolved: 0 or 1, where 0 is not resolved and 1 is resolved
        * (NOT YET IMPLEMENTED) limit: a positive integer, sets the maximum number of items to be returned.
        """
        query = model.Session.query(model.Todo)

        # check for a package ID or name in the request
        package_id = request.params.get('package')
        if package_id:
            # if a package was specified, make sure that it is 
            # a valid package ID/name
            package =  model.Package.get(package_id)
            if not package:
                return (404, {'error': "Package not found"})
            query = query.filter(model.Todo.package_id == package.id)

        return [{'category': get_category_name(todo.todo_category_id),
                 'description': todo.description,
                 'creator': get_user_full_name(todo.creator),
                 'created': todo.created.strftime('%d %h %Y')}
                for todo in query if query]

    @jsonify
    def category(self):
        """
        Return a list of todo all todo categories.
        """
        query = model.Session.query(model.TodoCategory)
        return [{'name': category.name} for category in query if query]
