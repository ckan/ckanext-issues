from ckan import model
import ckan.plugins as p
import ckanext.issues.model as issuemodel

def issue_auth(context, data_dict, privilege='package_update'):
    auth_data_dict = dict(data_dict)
    # we're checking package access so it is dataset/package id
    auth_data_dict['id'] = auth_data_dict['dataset_id']
    try:
        p.toolkit.check_access(privilege, context, auth_data_dict)
        return {'success': True}
    except p.toolkit.NotAuthorized:
        return {
            'success': False,
            'msg': p.toolkit._('User {0} not authorized for action on issue {1}'
                    .format(str(context['user']), data_dict['id']))
        }

@p.toolkit.auth_allow_anonymous_access
def issue_show(context, data_dict):
    return issue_auth(context, data_dict, 'package_show')

def issue_create(context, data_dict):
    # Any logged in user ...?
    return issue_auth(context, data_dict, 'package_create')

@p.toolkit.auth_disallow_anonymous_access
def issue_comment_create(context, data_dict):
    # Any logged in user ...?
    return issue_auth(context, data_dict, 'package_create')

@p.toolkit.auth_disallow_anonymous_access
def issue_update(context, data_dict):
    '''Checks that we can update the issue.

    Those with update rights on dataset (dataset 'editors') plus issue owner
    can do general updates

    Updating issue status is only dataset 'editors'
    '''
    # let's check if we're allowed to do everything
    out = issue_auth(context, data_dict, 'package_update')
    if out['success']:
        return out
    # now check if we created the issue
    issue = issuemodel.Issue.get(data_dict['id'])
    user = context['user']
    user_obj = model.User.get(user)
    if (
        (issue.user_id == user_obj.id) # we're the creator
        and # we are not trying to change status
        not (data_dict.get('status') and (issue.status != data_dict['status']))
        ):
        return {'success': True}
    # all other cases not allowed
    return {
        'success': False,
        'msg': p.toolkit._('User {0} not authorized for action on issue {1}'
                .format(str(user), data_dict['id']))
    }

def issue_delete(context, data_dict):
    return issue_auth(context, data_dict)

