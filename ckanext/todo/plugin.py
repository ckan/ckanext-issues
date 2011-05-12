"""
CKAN Todo Extension
"""
import os
from logging import getLogger
log = getLogger(__name__)

from genshi.input import HTML
from genshi.filters import Transformer
from pylons import request, tmpl_context as c
from webob import Request
from ckan.lib.base import h
from ckan.plugins import SingletonPlugin, implements
from ckan.plugins.interfaces import (IConfigurable, IRoutes, 
                                     IGenshiStreamFilter, IConfigurer)

from ckanext.todo import model
from ckanext.todo import controller
from ckanext.todo import html


class TodoPlugin(SingletonPlugin):
    """
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

        Create todo table in the database 
        """
        model.todo_category_table.create(checkfirst=True)
        model.todo_table.create(checkfirst=True)

    def before_map(self, map):
        """
        Expose the todo API.
        """
        return map

    def filter(self, stream):
        """
        Required to implement IGenshiStreamFilter.
        """
        routes = request.environ.get('pylons.routes_dict')
        return stream
