from ckan import model
import ckan.plugins as p
from ckanext.issues import model as issue_model

_ = p.toolkit._


def issue_auth(context, data_dict, privilege='package_update'):
    '''Returns whether the current user is allowed to do the action
    (privilege).'''
    auth_data_dict = dict(data_dict)
    # we're checking package access so it is dataset/package id
    auth_data_dict['id'] = auth_data_dict['dataset_id']
    try:
        p.toolkit.check_access(privilege, context, auth_data_dict)
        return {'success': True}
    except p.toolkit.NotAuthorized:
        return {
            'success': False,
            'msg': _(
                'User {user} not authorized for action on issue {issue}'
                ).format(
                user=str(context['user']),
                issue=auth_data_dict['id'])
        }


@p.toolkit.auth_allow_anonymous_access
def issue_show(context, data_dict):
    return issue_auth(context, data_dict, 'package_show')


@p.toolkit.auth_allow_anonymous_access
def issue_search(context, data_dict):
    try:
        p.toolkit.check_access('package_search', context, dict(data_dict))
        return {'success': True}
    except p.toolkit.NotAuthorized:
        return {
            'success': False,
            'msg': _('User {0} not authorized for action').format(
                str(context['user'])
            )
        }


def issue_create(context, data_dict):
    # Any logged in user
    return {'success': bool(context['user'])}


@p.toolkit.auth_disallow_anonymous_access
def issue_comment_create(context, data_dict):
    return {'success': True}
    # return issue_auth(context, data_dict, 'package_create')


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
    issue = issue_model.Issue.get_by_number(
        issue_number=data_dict['issue_number'],
        dataset_id=data_dict['dataset_id'],
    )
    user = context['user']
    if not issue:
        return {'success': False}
    user_obj = model.User.get(user)
    if ((issue.user_id == user_obj.id)  # we're the creator
       and  # we are not trying to change status
       not (data_dict.get('status')
            and (issue.status != data_dict['status']))):
        return {'success': True}
    # all other cases not allowed
    return {
        'success': False,
        'msg': _(
            'User {user} not authorized for action on issue {issue}'.format(
                user=str(user),
                issue=data_dict['issue_number'])
            )
    }


@p.toolkit.auth_disallow_anonymous_access
def issue_delete(context, data_dict):
    return issue_auth(context, data_dict)


@p.toolkit.auth_disallow_anonymous_access
def issue_report(context, data_dict):
    return {'success': True}


@p.toolkit.auth_disallow_anonymous_access
def issue_report_clear(context, data_dict):
    return {'success': True}


@p.toolkit.auth_disallow_anonymous_access
def issue_admin(context, data_dict):
    '''Who can administrate and issue

    sysadmins/organization admins and organization editors'''
    return issue_auth(context, data_dict)


@p.toolkit.auth_allow_anonymous_access
def issue_comment_search(context, data_dict):
    return {'success': True}
