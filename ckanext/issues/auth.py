import ckan.plugins as p


def issue_auth(context, data_dict, privilege='package_update'):
    # TODO: change package_id to id in context check ... ?
    user = context.get('user')

    authorized = p.toolkit.check_access(privilege, context, data_dict)

    if not authorized:
        return {
            'success': False,
            'msg': p.toolkit._('User {0} not authorized to update resource {1}'
                    .format(str(user), data_dict['id']))
        }
    else:
        return {'success': True}


def issue_create(context, data_dict):
    return issue_auth(context, data_dict)


def issue_upsert(context, data_dict):
    return issue_auth(context, data_dict)

def issue_delete(context, data_dict):
    return issue_auth(context, data_dict)

def issue_change_status(context, data_dict):
    return issue_auth(context, data_dict)

