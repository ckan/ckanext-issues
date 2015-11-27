"""
CKAN Issue Extension
"""
from logging import getLogger
log = getLogger(__name__)

import ckan.plugins as p
from ckan.plugins import implements, toolkit

from ckanext.issues.lib import util, helpers
from ckanext.issues.model import setup as model_setup
import ckanext.issues.logic.action as action
import ckanext.issues.auth as auth


class IssuesPlugin(p.SingletonPlugin):
    """
    CKAN Issues Extension
    """
    implements(p.IConfigurer, inherit=True)
    implements(p.ITemplateHelpers, inherit=True)
    implements(p.IConfigurable)
    implements(p.IRoutes, inherit=True)
    implements(p.IActions)
    implements(p.IAuthFunctions)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public/css')
        toolkit.add_resource('public/scripts', 'ckanext_issues')

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'issues_installed': lambda: True,
            'issue_count': util.issue_count,
            'issue_comment_count': util.issue_comment_count,
            'issues_enabled_for_organization':
                helpers.issues_enabled_for_organization,
            'replace_url_param': helpers.replace_url_param,
            'get_issue_filter_types': helpers.get_issue_filter_types,
            'get_issues_per_page': helpers.get_issues_per_page,
            'issues_enabled': helpers.issues_enabled,
            'issues_list': helpers.issues_list,
            'issues_user_has_reported_issue':
                helpers.issues_user_has_reported_issue,
            'issues_user_is_owner':
                helpers.issues_user_is_owner,
            'issues_users_who_reported_issue':
                helpers.issues_users_who_reported_issue,
        }

    # IConfigurable

    def configure(self, config):
        """
        Called by load_environment
        """
        model_setup()

    # IRoutes

    def before_map(self, map):
        from ckan.config.routing import SubMapper

        controller_name = 'ckanext.issues.controller:IssueController'
        with SubMapper(map, controller=controller_name) as m:
            m.connect('issues_dataset',
                      '/dataset/:dataset_id/issues',
                      action='dataset',
                      ckan_icon='warning-sign')
            m.connect('issues_new',
                      '/dataset/:dataset_id/issues/new',
                      action='new')
            m.connect('issues_edit',
                      '/dataset/:dataset_id/issues/:issue_number/edit',
                      action='edit')
            m.connect('issues_delete',
                      '/dataset/:dataset_id/issues/:issue_number/delete',
                      action='delete')
            m.connect('issues_assign',
                      '/dataset/:dataset_id/issues/:issue_number/assign',
                      action='assign')
            m.connect('issues_comments',
                      '/dataset/:dataset_id/issues/:issue_number/comments',
                      action='comments')
            m.connect('issues_report',
                      '/dataset/:dataset_id/issues/:issue_number/report',
                      action='report'),
            m.connect('issues_report_clear',
                      '/dataset/:dataset_id/issues/:issue_number/report_clear',
                      action='report_clear'),
            m.connect('issues_comment_report',
                      '/dataset/:dataset_id/issues/:issue_number/comment/:comment_id/report',
                      action='report_comment'),
            m.connect('issues_comment_report_clear',
                      '/dataset/:dataset_id/issues/:issue_number/comment/:comment_id/report_clear',
                      action='comment_report_clear'),
            m.connect('add_issue_with_resource',
                      '/dataset/:dataset_id/issues/new/:resource_id',
                      action='add')
            m.connect('issues_show',
                      '/dataset/:dataset_id/issues/:issue_number',
                      action='show')
            m.connect('all_issues_page', '/issues', action='all_issues_page')
            m.connect('issues_for_organization',
                      '/organization/:org_id/issues',
                      action='issues_for_organization')

        moderation = 'ckanext.issues.controller:ModerationController'
        with SubMapper(map, controller=moderation) as m:
            m.connect('issues_moderate_reported_issues',
                      '/organization/:organization_id/issues/reported',
                      action='all_reported_issues')
            m.connect('issues_moderate',
                      '/organization/:organization_id/issues/moderate',
                      action='moderate')

        moderation = 'ckanext.issues.controller:CommentModerationController'
        with SubMapper(map, controller=moderation) as m:
            m.connect('issues_moderate_reported_comments',
                      '/organization/:organization_id/issues/reported_comments',
                      action='reported_comments')
            m.connect('issues_moderate_comment',
                      '/organization/:organization_id/issues/moderate_comment',
                      action='moderate')

        return map

    # IActions

    def get_actions(self):
        return dict((name, function) for name, function
                    in action.__dict__.items()
                    if callable(function))

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'issue_admin': auth.issue_admin,
            'issue_search': auth.issue_search,
            'issue_show': auth.issue_show,
            'issue_create': auth.issue_create,
            'issue_comment_create': auth.issue_comment_create,
            'issue_update': auth.issue_update,
            'issue_delete': auth.issue_delete,
            'issue_report': auth.issue_report,
            'issue_report_clear': auth.issue_report_clear,
            'issue_comment_search': auth.issue_comment_search,
        }
