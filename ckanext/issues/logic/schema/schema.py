__all__ = ['issue_update_schema']

from ckan.plugins import toolkit

not_missing = toolkit.get_validator('not_missing')
ignore_missing = toolkit.get_validator('ignore_missing')
package_exists = toolkit.get_validator('package_id_or_name_exists')
resource_id_exists = toolkit.get_validator('resource_id_exists')
user_exists = toolkit.get_validator('user_id_or_name_exists')


def issue_update_schema():
    return {
        'id': [not_missing, unicode],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'dataset_id': [ignore_missing, unicode, package_exists],
        'resource_id': [ignore_missing, unicode, resource_id_exists],
        'resolver_id': [ignore_missing, unicode, user_exists],
        'status':  [ignore_missing, unicode],
    }
