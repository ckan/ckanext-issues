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
    return query.first().display_name if query.first() else None

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

        return [{'category': model.TodoCategory.get(todo.todo_category_id).name,
                 'description': todo.description,
                 'creator': get_user_full_name(todo.creator),
                 'created': todo.created.strftime('%d %h %Y')}
                for todo in query if query]

    @jsonify
    def post(self):
        """
        Add a new todo item.

        Todo items must have a category, description and a creator. Other fields
        are optional.
        """
        # check for a category name
        category_name = request.params.get('category_name')
        if not category_name:
            response.status_int = 400
            return {'error': "No category name given"}

        # check for a description
        description = request.params.get('description')
        if not description:
            response.status_int = 400
            return {'error': "No description given"}

        # check for a creator
        creator = request.params.get('creator')
        if not creator:
            response.status_int = 400
            return {'error': "No creator given"}

        # check that creator matches the current user
        current_user = model.User.get(request.environ.get('REMOTE_USER'))
        if not current_user:
            response.status_int = 403
            return {'error': "You are not authorized to make this request"}
        if not creator == current_user.id:
            response.status_int = 403
            return {'error': "You are not authorized to make this request"}

        # check for a package ID or name in the request
        package_name = request.params.get('package_name')
        if package_name:
            # if a package was specified, make sure that it is 
            # a valid package ID/name
            package =  model.Package.get(package_name)
            if not package:
                response.status_int = 400
                return {'error': "Invalid package name or ID"}

        return {}
        session = model.meta.Session()

        # if category doesn't already exist, create it
        category = model.TodoCategory.get(category_name)
        if not category:
            try:
                category = model.TodoCategory(unicode(category_name))
                session.add(category)
                session.commit()
            except Exception as e:
                log.warn("Database Error: " + str(e))
                session.rollback()
                response.status_int = 500
                return {'error': "Could not add category to database"}

        # add new item to database
        try:
            t = model.Todo(category.id, description, creator)
            t.package_id = package.id if package else None
            session.add(t)
            session.commit()
        except Exception as e:
            log.warn("Database Error: " + str(e))
            session.rollback()
            response.status_int = 500
            return {'error': "Could not add todo item to database"}

        return {}

    @jsonify
    def category(self):
        """
        Return a list of todo all todo categories.
        """
        query = model.Session.query(model.TodoCategory)
        return [{'name': category.name} for category in query if query]
