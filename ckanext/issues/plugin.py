"""
CKAN Issue Extension
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

from ckanext.issues import model
from ckanext.issues import controller
from ckanext.issues import html


class IssuesPlugin(SingletonPlugin):
    """
    CKAN Issues Extension
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

        Create issue and issue_category tables in the database.
        Prepopulate issue_category table with default categories.
        """
        model.issue_category_table.create(checkfirst=True)
        model.issue_table.create(checkfirst=True)
        # add default categories if they don't already exist
        session = model.meta.Session()
        for category_name in model.DEFAULT_CATEGORIES:
            category = model.IssueCategory.get(category_name)
            if not category:
                category = model.IssueCategory(category_name)
                session.add(category)
        session.commit()
            
    def before_map(self, map):
        """
        Expose the issue API.
        """
        map.connect('issue', '/api/2/issue',
                    controller='ckanext.issues.controller:IssueController',
                    action='get', 
                    conditions=dict(method=['GET']))
        map.connect('issue_post', '/api/2/issue',
                    controller='ckanext.issues.controller:IssueController',
                    action='post', 
                    conditions=dict(method=['POST']))
        map.connect('issue_resolve', '/api/2/issue/resolve',
                    controller='ckanext.issues.controller:IssueController',
                    action='resolve', 
                    conditions=dict(method=['POST']))
        map.connect('issue_category', '/api/2/issue/category',
                    controller='ckanext.issues.controller:IssueController',
                    action='category', 
                    conditions=dict(method=['GET']))
        map.connect('issue_autocomplete', '/api/2/issue/autocomplete',
                    controller='ckanext.issues.controller:IssueController',
                    action='autocomplete')
        map.connect('issue_page', '/issue',
                    controller='ckanext.issues.controller:IssueController',
                    action='issue_page')
        return map

    def filter(self, stream):
        """
        Implements IGenshiStreamFilter.
        """
        routes = request.environ.get('pylons.routes_dict')

        # add a 'Issue' link to the menu bar
        menu_data = {'href': 
            h.link_to("Issue", h.url_for('issue_page'), 
                class_ = ('active' if c.controller == 'ckanext.issues.controller:IssueController' else ''))}

        stream = stream | Transformer('body//div[@id="mainmenu"]')\
            .append(HTML(html.MENU_CODE % menu_data))

        # if this is the read action of a package, show issue info
        if(routes.get('controller') == 'package' and
           routes.get('action') == 'read' and 
           c.pkg.id):
            user_id = controller.get_user_id(request.environ.get('REMOTE_USER')) or ""
            data = {'package': c.pkg.name,
                    'user_id': user_id}
            # add CSS style
            stream = stream | Transformer('head').append(HTML(html.HEAD_CODE))
            # add jquery and issue.js links
            stream = stream | Transformer('body').append(HTML(html.BODY_CODE % data))
            # add issue subsection
            stream = stream | Transformer('//div[@id="dataset"]')\
                .append(HTML(html.ISSUE_CODE))
        return stream
