"""
CKAN Issue Extension
"""
import os
from logging import getLogger
log = getLogger(__name__)

import ckan.plugins as p
from ckan.plugins import implements, toolkit

from ckanext.issues.lib import util
from ckanext.issues import model
from ckanext.issues import controller

class IssuesPlugin(p.SingletonPlugin):
    """
    CKAN Issues Extension
    """
    implements(p.IConfigurable)
    implements(p.IConfigurer, inherit=True)
    implements(p.IRoutes, inherit=True)
    implements(p.ITemplateHelpers, inherit=True)

    def update_config(self, config):
        """
        Called during CKAN setup.

        Add the public folder to CKAN's list of public folders,
        and add the templates folder to CKAN's list of template
        folders.
        """
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

    def get_helpers(self):
        """
        A dictionary of extra helpers that will be available to provide
        ga report info to templates.
        """
        return {
            'issues_installed': lambda: True,
            'issue_count': util.issue_count,
            'issue_comment_count': util.issue_comment_count,
        }

    def configure(self, config):
        """
        Called at the end of CKAN setup.

        Create issue and issue_category tables in the database.
        Prepopulate issue_category table with default categories.
        """
        model.issue_category_table.create(checkfirst=True)
        model.issue_table.create(checkfirst=True)
        model.issue_comment_table.create(checkfirst=True)

        # add default categories if they don't already exist
        session = model.meta.Session()
        for category_name, category_desc in model.DEFAULT_CATEGORIES.iteritems():
            if not category_name:
                continue

            category = model.IssueCategory.get(category_name)
            if not category:
                category = model.IssueCategory(category_name)
                category.description = category_desc
                session.add(category)
        session.commit()

    def before_map(self, map):
        """
        Expose the issue API.
        """
        from ckan.config.routing import SubMapper

        with SubMapper(map, controller='ckanext.issues.controller:IssueAPIController', path_prefix='/api/2') as m:
            m.connect('issue', '/issue',
                        action='get',
                        conditions=dict(method=['GET']))
            m.connect('issue_post', '/issue',
                        action='post',
                        conditions=dict(method=['POST']))
            m.connect('issue_resolve', '/issue/resolve',
                        action='resolve',
                        conditions=dict(method=['POST']))
            m.connect('issue_category', '/issue/category',
                        action='category',
                        conditions=dict(method=['GET']))
            m.connect('issue_autocomplete', '/issue/autocomplete',
                        action='autocomplete')

        with SubMapper(map, controller='ckanext.issues.controller:IssueController') as m:
            m.connect('issue_page', '/dataset/:package_id/issues', action='issue_page')
            m.connect('add_issue', '/dataset/:package_id/issues/add', action='add')
            m.connect('add_issue_with_resource', '/dataset/:package_id/issues/add/:resource_id', action='add')
            m.connect('all_issues_page', '/dataset/issues/all', action='all_issues_page')
            m.connect('publisher_issue_page', '/publisher/issues/:publisher_id', action='publisher_issue_page')


        return map
