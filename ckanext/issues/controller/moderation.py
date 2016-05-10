from ckan.plugins import toolkit
import ckan.lib.helpers as h

class ModerationController(toolkit.BaseController):

    def index(self):
        ''' Base moderation page for ALL Issues and Comments.
           POST requests will  be to either delete the item, or to
           mark it as not spam (with Akismet)'''

        try:
            page = int(toolkit.request.params.get('page', 1))
            page = page or 1  # 0 is not valid
        except:
            page = 1

        offset = (page * 10) - 10

        if not toolkit.c.user:
            msg = toolkit._('You must be logged in to moderate issues and comments')
            toolkit.abort(401, msg)

        issues = toolkit.get_action('issue_search')(data_dict={
            'visibility': 'hidden',
            'offset': offset,
            'limit': 10,
        })
        comments = toolkit.get_action('issue_comment_search')(data_dict={
            'only_hidden': True,
            'offset': offset,
            'limit' : 10
        })
        print(comments)
        extra_vars = {
            'issues': issues.get('results'),
            'comments': comments.get('results'),
        }

        return toolkit.render('issues/moderation_all.html',
                                extra_vars=extra_vars)

    def moderate_comment_delete(self, id):
        toolkit.get_action('issue_comment_delete')(data_dict={'comment_id': id})
        h.redirect_to('issues_moderation')

    def moderate_comment_reset(self, id):
        toolkit.get_action('issue_comment_report_clear')(data_dict={'comment_id': id})
        h.redirect_to('issues_moderation')

    def moderate_issue_delete(self, id):
        import ckanext.issues.model as issuemodel
        issue = issuemodel.Issue.get(id)
        toolkit.get_action('issue_delete')(data_dict={
            'dataset_id': issue.dataset_id,
            'issue_number': issue.number,
        })
        h.redirect_to('issues_moderation')

    def moderate_issue_reset(self, id):
        import ckanext.issues.model as issuemodel
        issue = issuemodel.Issue.get(id)
        toolkit.get_action('issue_report_clear')(data_dict={
            'dataset_id': issue.dataset_id,
            'issue_number': issue.number,
        })
        h.redirect_to('issues_moderation')

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
    def reported_comments(self, organization_id):
        try:
            organization = toolkit.get_action('organization_show')(data_dict={
                'id': organization_id,
            })
            comments = toolkit.get_action('issue_comment_search')(data_dict={
                'organization_id': organization['id'],
                'only_hidden': True,
            })

            return toolkit.render(
                'issues/comment_moderation.html',
                extra_vars={
                    'comments': comments.get('results'),
                    'organization': organization,
                }
            )
        except toolkit.ObjectNotFound:
            toolkit.abort(404, toolkit._('Organization not found'))

    def moderate(self, organization_id):
        if toolkit.request.method == 'POST':
            if not toolkit.c.user:
                msg = toolkit._('You must be logged in to moderate comment')
                toolkit.abort(401, msg)

            data_dict = toolkit.request.POST.mixed()
            try:
                if data_dict.get('abuse_status') == 'abuse':
                    toolkit.get_action('issue_comment_report')(data_dict=data_dict)
                    h.flash_success(toolkit._('Comment permanently hidden'))
                elif data_dict.get('abuse_status') == 'not_abuse':
                    toolkit.get_action('issue_comment_report_clear')(
                        data_dict=data_dict)
                    h.flash_success(toolkit._('All comment reports cleared'))
            except toolkit.ValidationError:
                toolkit.abort(404)

        h.redirect_to('issues_moderate_reported_comments',
                      organization_id=organization_id)
