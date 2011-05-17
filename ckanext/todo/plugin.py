"""
CKAN Todo Extension
"""
import os
from logging import getLogger
log = getLogger(__name__)

from genshi.input import HTML
from genshi.filters import Transformer
from pylons import request, tmpl_context as c
from ckan.lib.base import h
from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.interfaces import (IConfigurable, IRoutes, 
                                     IGenshiStreamFilter, IConfigurer)

from ckanext.todo import model
from ckanext.todo import controller
from ckanext.todo import html


class TodoPlugin(SingletonPlugin):
    """
    CKAN Todo Extension
    """
    implements(IConfigurable)
    implements(IConfigurer, inherit=True)
    implements(IRoutes, inherit=True)
    implements(IGenshiStreamFilter)

    def update_config(self, config):
        """
        Called during CKAN setup.

        Add the public folder to CKAN's list of public folders,
        and add the templates folder to CKAN's list of template
        folders.
        """
        # add public folder to the CKAN's list of public folders
        here = os.path.dirname(__file__)
        public_dir = os.path.join(here, 'public')
        if config.get('extra_public_paths'):
            config['extra_public_paths'] += ',' + public_dir
        else:
            config['extra_public_paths'] = public_dir
        # add template folder to the CKAN's list of template folders
        template_dir = os.path.join(here, 'templates')
        if config.get('extra_template_paths'):
            config['extra_template_paths'] += ',' + template_dir
        else:
            config['extra_template_paths'] = template_dir

    def configure(self, config):
        """
        Called at the end of CKAN setup.

        Create todo and todo_category tables in the database.
        Prepopulate todo_category table with default categories.
        """
        model.todo_category_table.create(checkfirst=True)
        model.todo_table.create(checkfirst=True)
        # add default categories if they don't already exist
        session = model.meta.Session()
        for category_name in model.DEFAULT_CATEGORIES:
            category = model.TodoCategory.get(category_name)
            if not category:
                category = model.TodoCategory(category_name)
                session.add(category)
        session.commit()
            
    def before_map(self, map):
        """
        Expose the todo API.
        """
        map.connect('todo', '/api/2/todo',
                    controller='ckanext.todo.controller:TodoController',
                    action='get', 
                    conditions=dict(method=['GET']))
        map.connect('todo_post', '/api/2/todo',
                    controller='ckanext.todo.controller:TodoController',
                    action='post', 
                    conditions=dict(method=['POST']))
        map.connect('todo_resolve', '/api/2/todo/resolve',
                    controller='ckanext.todo.controller:TodoController',
                    action='resolve', 
                    conditions=dict(method=['POST']))
        map.connect('todo_category', '/api/2/todo/category',
                    controller='ckanext.todo.controller:TodoController',
                    action='category', 
                    conditions=dict(method=['GET']))
        map.connect('todo_page', '/todo',
                    controller='ckanext.todo.controller:TodoController',
                    action='todo_page')
        return map

    def filter(self, stream):
        """
        Implements IGenshiStreamFilter.
        """
        routes = request.environ.get('pylons.routes_dict')

        # add a 'Todo' link to the menu bar
        menu_data = {'href': 
            h.nav_link(c, "Todo", 
                controller='ckanext.todo.controller:TodoController', 
                action='todo_page')}
        stream = stream | Transformer('body//div[@class="menu"]/ul]')\
            .append(HTML(html.MENU_CODE % menu_data))

        # if this is the read action of a package, show todo info
        if(routes.get('controller') == 'package' and
           routes.get('action') == 'read' and 
           c.pkg.id):
            user_id = controller.get_user_id(request.environ.get('REMOTE_USER')) or ""
            data = {'package': c.pkg.name,
                    'user_id': user_id}
            # add CSS style
            stream = stream | Transformer('head').append(HTML(html.HEAD_CODE))
            # add jquery and todo.js links
            stream = stream | Transformer('body').append(HTML(html.BODY_CODE % data))
            # add the todo count to the package title, after the RSS 'subscribe' link
            stream = stream | Transformer('body//div[@id="package"]//h2[@class="head"]')\
                .append(HTML(html.TODO_COUNT_CODE))
            # add todo subsection
            stream = stream | Transformer('body//div[@id="package"]')\
                .append(HTML(html.TODO_CODE))
        return stream
