import ckan.plugins as p


def issue_auth(context, data_dict, privilege='package_update'):
    auth_data_dict = dict(data_dict)
    # we're checking package access so it is dataset/package id
    auth_data_dict['id'] = auth_data_dict['dataset_id']
    authorized = p.toolkit.check_access(privilege, context, auth_data_dict)
    if not authorized:
        return {
            'success': False,
            'msg': p.toolkit._('User {0} not authorized for action on issue {1}'
                    .format(str(user), data_dict['id']))
        }
    else:
        return {'success': True}

@p.toolkit.auth_allow_anonymous_access
def issue_show(context, data_dict):
    return issue_auth(context, data_dict, 'package_show')

def issue_create(context, data_dict):
    # Any logged in user ...?
    return issue_auth(context, data_dict, 'package_create')

def issue_comment_create(context, data_dict):
    # Any logged in user ...?
    return issue_auth(context, data_dict, 'package_create')

def issue_upsert(context, data_dict):
    return issue_auth(context, data_dict)

def issue_delete(context, data_dict):
    return issue_auth(context, data_dict)

def issue_change_status(context, data_dict):
    return issue_auth(context, data_dict)

