from ckan.plugins import toolkit
import ckan.lib.helpers as h

try:
    import ckan.authz as authz
except ImportError:
    import ckan.new_authz as authz

from ckanext.issues.lib.helpers import Pagination

class ModerationController(toolkit.BaseController):

    def _get_page(self, name):
        try:
            page = int(toolkit.request.params.get(name))
            if page < 1:
                page = 1
        except Exception, e:
            page = 1
        return page

    def index(self):
        ''' Base moderation page for ALL Issues and Comments.
           POST requests will  be to either delete the item, or to
           mark it as not spam (with Akismet)'''
        if not authz.is_sysadmin(toolkit.c.user):
            msg = toolkit._('You must be logged in to moderate issues and comments')
            toolkit.abort(401, msg)

        ipage = self._get_page('ipage')
        cpage = self._get_page('cpage')

        per_page = 5

        issues = toolkit.get_action('issue_search')(data_dict={
            'visibility': 'hidden',
            'offset': (ipage * per_page) - per_page,
            'limit': per_page
        })
        comments = toolkit.get_action('issue_comment_search')(data_dict={
            'only_hidden': True,
            'offset': (cpage * per_page) - per_page,
            'limit': per_page
        })

        extra_vars = {
            'ipage': ipage,
            'issue_pages': Pagination(ipage, per_page, issues.get('count')),
            'issues': issues,
            'cpage': cpage,
            'comments_pages': Pagination(cpage, per_page, comments.get('count')),
            'comments': comments,
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
                    'comments': comments,
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
