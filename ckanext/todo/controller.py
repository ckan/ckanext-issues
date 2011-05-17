"""
CKAN Todo Extension
"""
from logging import getLogger
log = getLogger(__name__)

from sqlalchemy import func
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
        * category: a category ID or name 
        * resolved: 0 or 1, where 0 is not resolved and 1 is resolved
        * limit: a positive integer, sets the maximum number of items to be returned.
        """
        query = model.Session.query(model.Todo).order_by(model.Todo.created.desc())

        # check for a package ID or name in the request
        package_id = request.params.get('package')
        if package_id:
            # if a package was specified, make sure that it is 
            # a valid package ID/name
            package =  model.Package.get(package_id)
            if not package:
                response.status_int = 404
                return {'error': "Package not found"}
            query = query.filter(model.Todo.package_id == package.id)

        # check for a category
        category_name_or_id = request.params.get('category')
        if category_name_or_id:
            category = model.TodoCategory.get(category_name_or_id)
            if not category:
                response.status_int = 404
                return {'error': "Category not found"}
            query = query.filter(model.Todo.todo_category_id == category.id)

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
                query = query.filter(model.Todo.resolved != None)
            else:
                query = query.filter(model.Todo.resolved == None)

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

        return [{'id': todo.id,
                 'category': model.TodoCategory.get(todo.todo_category_id).name,
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
    def resolve(self):
        """
        Resolve a todo item.
        """
        # check for a todo ID
        todo_id = request.params.get('todo_id')
        if not todo_id:
            response.status_int = 400
            return {'error': "No todo ID given"}

        # make sure todo ID is valid
        todo = model.Todo.get(todo_id)
        if not todo:
            response.status_int = 400
            return {'error': "Invalid todo ID"}

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
            todo.resolved = model.datetime.now()
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

    def todo_page(self):
        """
        Display a page containing a list of all todo items.
        """
        # categories
        categories = model.Session.query(func.count(model.Todo.id).label('todo_count'), 
                                         model.Todo.todo_category_id)\
            .filter(model.Todo.resolved == None)\
            .group_by(model.Todo.todo_category_id)
        c.categories = []
        c.pkg_names = {}
        for t in categories:
            tc = model.TodoCategory.get(t.todo_category_id)
            tc.todo_count = t.todo_count
            # get todo items for each category
            tc.todo = model.Session.query(model.Todo).filter(model.Todo.resolved == None)\
                .filter(model.Todo.todo_category_id == t.todo_category_id)\
                .order_by(model.Todo.created.desc())
            for todo in tc.todo:
                # get the package name for each package if one exists
                if todo.package_id:
                    c.pkg_names[todo.package_id] = model.Package.get(todo.package_id).name
            c.categories.append(tc)
        # sort into alphabetical order
        c.categories.sort(key = lambda x: x.name)
        return render("todo.html")
