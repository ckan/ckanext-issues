from ckan import model
from ckan import logic
from ckan.logic import action
import ckan.plugins as p
import ckanext.issues.model as issuemodel
from pylons import config
import logging

log = logging.getLogger(__name__)

supported_roles = ["Anonymous","Member","Editor","Admin"]

def _guess_issue_id(data_dict):

    issue_id = None

    # Dataset owner shall not change status
    if 'id' in data_dict:
        issue_id = data_dict['id']
    elif 'issue_id' in data_dict and not 'id' in data_dict:
        issue_id = data_dict['issue_id']

    return issue_id

def is_changing_status(data_dict):

    issue_id = _guess_issue_id(data_dict)

    issue = issuemodel.Issue.get(issue_id)

    if data_dict.get('status') and (issue.status != data_dict['status']):
        return True

    return False

def is_dataset_creator(context,data_dict):

    dataset_obj = model.Package.get(data_dict['dataset_id'])
    user = context['user']
    user_obj = model.User.get(user)

    return dataset_obj.creator_user_id == user_obj.id


def _issue_auth_status_change(context,data_dict):

    issue_id = _guess_issue_id(data_dict)

    if is_dataset_creator(context,data_dict):
        return {'success': False,
                'msg': p.toolkit._('Dataset owner is not allowed to change status of issue {0}'
                        .format(issue_id))
                }

    return _issue_auth_read_and_create(context,data_dict)

def _issue_auth_read_and_create(context,data_dict):

    # Check ckanext.issues.minimun_role_required, default to Anonymous
    minimun_role_required = config.get("ckanext.issues.minimun_role_required", "Anonymous")

    # invalid config value
    if minimun_role_required not in supported_roles:
        log.error(p.toolkit._('Value {0} for ckanext.issues.minimun_role_required not valid. Allowed values: {1}'
                .format(minimun_role_required, str(supported_roles))))
        return {
            'success': False,
            'msg': p.toolkit._('Value {0} for ckanext.issues.minimun_role_required not valid. Allowed values: {1}'
                    .format(minimun_role_required, str(supported_roles)))
        }

    # Not logged in
    if context.get('auth_user_obj') is None:
        return {'success': False,
                'msg': p.toolkit._("You must be logged in to report access issues information")}

    dataset_obj = model.Package.get(data_dict['dataset_id'])
    user = context['user']
    user_obj = model.User.get(user)
    is_dataset_creator = dataset_obj.creator_user_id == user_obj.id

    if is_dataset_creator:
        return {'success': True}

    if minimun_role_required == "Anonymous":
        return {'success': True}
    elif minimun_role_required == "Member":
        return issue_auth_package(context, data_dict, 'package_show')
    elif minimun_role_required == "Editor":
        return issue_auth_package(context, data_dict, 'package_update')
    elif minimun_role_required == "Admin":
        return issue_auth_organization(context, data_dict, 'organization_update')

    return {
        'success': False,
        'msg': p.toolkit._('User {0} not authorized for action on issue {1}'
                .format(str(context['user']), data_dict['id']))
    }

def issue_auth_package(context, data_dict, privilege='package_update'):
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
                    .format(str(context['user']), auth_data_dict['id']))
        }

def issue_auth_organization(context, data_dict, privilege='organization_update'):
    auth_data_dict = dict(data_dict)
    # we're checking package access so it is dataset/package id
    auth_data_dict['id'] = auth_data_dict['dataset_id']

    # Obtain dataset's owner organization's id
    try:
        dataset = action.get.package_show(context,auth_data_dict)
        auth_data_dict['id'] = dataset['owner_org']
    except logic.NotFound:
        return {
            'success': False,
            'msg': p.toolkit._('Dataset {0} not found, therefore user cannot be authorized'
                    .format(auth_data_dict['id']))
        }

    try:
        p.toolkit.check_access(privilege, context, auth_data_dict)
        return {'success': True}
    except p.toolkit.NotAuthorized:
        return {
            'success': False,
            'msg': p.toolkit._('User {0} not authorized for action on issue {1}'
                    .format(str(context['user']), auth_data_dict['id']))
        }

@p.toolkit.auth_allow_anonymous_access
def issue_list(context, data_dict):

    return _issue_auth_read_and_create(context,data_dict)

@p.toolkit.auth_allow_anonymous_access
def issue_show(context, data_dict):

    return _issue_auth_read_and_create(context,data_dict)

def issue_create(context, data_dict):

    return _issue_auth_read_and_create(context,data_dict)

@p.toolkit.auth_disallow_anonymous_access
def issue_comment_create(context, data_dict):

    return _issue_auth_read_and_create(context,data_dict)

@p.toolkit.auth_disallow_anonymous_access
def issue_update(context, data_dict):

    if is_changing_status(data_dict):
        return _issue_auth_status_change(context,data_dict)

    return _issue_auth_read_and_create(context,data_dict)

@p.toolkit.auth_disallow_anonymous_access
def issue_delete(context, data_dict):

    return _issue_auth_status_change(context,data_dict)

def issue_report_spam(context, data_dict):

    return _issue_auth_read_and_create(context,data_dict)

@p.toolkit.auth_disallow_anonymous_access
def issue_reset_spam_state(context, data_dict):

    return _issue_auth_read_and_create(context,data_dict)
