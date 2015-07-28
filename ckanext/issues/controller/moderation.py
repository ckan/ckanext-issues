from ckan.plugins import toolkit
import ckan.lib.helpers as h


class ModerationController(toolkit.BaseController):
    def all_reported_issues(self, organization_id):
        '''show all issues over max_strikes and are not moderated'''
        try:
            issues, organization = all_reported_issues(organization_id)
            extra_vars = {
                'issues': issues.get('results', []),
                'organization': organization,
            }
            return toolkit.render("issues/moderation.html",
                                  extra_vars=extra_vars)
        except toolkit.ObjectNotFound:
            toolkit.abort(404, toolkit._('Organization not found'))

    def moderate(self, organization_id):
        if toolkit.request.method == 'POST':
            if not toolkit.c.user:
                msg = toolkit._('You must be logged in to moderate issues')
                toolkit.abort(401, msg)

            data_dict = toolkit.request.POST.mixed()
            try:
                if data_dict.get('abuse_status') == 'abuse':
                    toolkit.get_action('issue_report')(data_dict=data_dict)
                    h.flash_success(toolkit._('Issue permanently hidden'))
                elif data_dict.get('abuse_status') == 'not_abuse':
                    toolkit.get_action('issue_report_clear')(
                        data_dict=data_dict)
                    h.flash_success(toolkit._('All issue reports cleared'))
            except toolkit.ValidationError:
                toolkit.abort(404)

        h.redirect_to('issues_moderate_reported_issues',
                      organization_id=organization_id)


def all_reported_issues(organization_id, include_sub_organizations=False):
    organization = toolkit.get_action('organization_show')(data_dict={
        'id': organization_id,
    })

    issues = toolkit.get_action('issue_search')(data_dict={
        'organization_id': organization['id'],
        'abuse_status': 'unmoderated',
        'include_reports': True,
        'include_sub_organizations': include_sub_organizations,
        'visibility': 'hidden',
    })

    return issues, organization


class CommentModerationController(toolkit.BaseController):
    pass
