from ckan.plugins import toolkit
from ckanext.issues.logic.validators import (
    as_package_id,
    as_org_id,
    is_valid_sort,
    is_valid_status,
    is_valid_abuse_status,
    issue_exists,
    issue_comment_exists,
    issue_number_exists_for_dataset,
)

not_missing = toolkit.get_validator('not_missing')
ignore_missing = toolkit.get_validator('ignore_missing')
package_exists = toolkit.get_validator('package_id_or_name_exists')
resource_id_exists = toolkit.get_validator('resource_id_exists')
user_exists = toolkit.get_validator('user_id_or_name_exists')
organization_exists = toolkit.get_validator('group_id_or_name_exists')
is_natural_number = toolkit.get_validator('natural_number_validator')
is_positive_integer = toolkit.get_validator('is_positive_integer')
boolean_validator = toolkit.get_validator('boolean_validator')


def issue_show_schema():
    return {
        'dataset_id': [not_missing, unicode, package_exists, as_package_id],
        'include_reports': [ignore_missing, bool],
        'issue_number': [not_missing, is_positive_integer],
        '__after': [issue_number_exists_for_dataset],
    }


def issue_create_schema():
    return {
        'title': [not_missing, unicode],
        'description': [ignore_missing, unicode],
        'dataset_id': [not_missing, unicode, package_exists, as_package_id],
    }


def issue_update_schema():
    return {
        'assignee_id': [ignore_missing, unicode, user_exists],
        'dataset_id': [not_missing, unicode, package_exists, as_package_id],
        'description': [ignore_missing, unicode],
        'issue_number': [not_missing, is_positive_integer],
        'resource_id': [ignore_missing, unicode, resource_id_exists],
        'status':  [ignore_missing, unicode],
        'title': [ignore_missing, unicode],
        '__after': [issue_number_exists_for_dataset],
    }


def issue_delete_schema():
    return {
        'issue_number': [not_missing, is_positive_integer],
        'dataset_id': [not_missing, unicode, package_exists, as_package_id],
        '__after': [issue_number_exists_for_dataset],
    }


def issue_search_schema():
    return {
        'dataset_id': [ignore_missing, unicode, as_package_id],
        'organization_id': [ignore_missing, unicode, as_org_id],
        'status': [ignore_missing, unicode, is_valid_status],
        'sort': [ignore_missing, unicode, is_valid_sort],
        'limit': [ignore_missing, is_natural_number],
        'offset': [ignore_missing, is_natural_number],
        'q': [ignore_missing, unicode],
        'visibility': [ignore_missing, unicode],
        'include_count': [ignore_missing, bool],
        'include_datasets': [ignore_missing, bool],
        'include_reports': [ignore_missing, bool],
        'include_results': [ignore_missing, bool],
        'include_sub_organizations': [ignore_missing, bool],
        'abuse_status': [ignore_missing, unicode, is_valid_abuse_status],
    }


def issue_comment_schema():
    return {
        'comment': [not_missing, unicode],
        'dataset_id': [not_missing, unicode, package_exists, as_package_id],
        'issue_number': [not_missing, is_positive_integer],
        '__after': [issue_number_exists_for_dataset],
    }


def issue_report_schema():
    return {
        'dataset_id': [not_missing, unicode, package_exists, as_package_id],
        'issue_number': [not_missing, is_positive_integer],
        '__after': [issue_number_exists_for_dataset],
    }


def issue_report_clear_schema():
    schema = issue_report_schema()
    schema.update({'clear_abuse_status': [ignore_missing, bool]})
    return schema


def issue_comment_report_schema():
    return {
        'dataset_id': [not_missing, unicode, package_exists, as_package_id],
        'issue_number': [not_missing, is_positive_integer],
        '__after': [issue_number_exists_for_dataset],
        'comment_id': [not_missing, unicode, issue_comment_exists],
    }

def issue_comment_report_clear_schema():
    return {
        'comment_id': [not_missing, unicode, issue_comment_exists],
    }

def issue_comment_delete_schema():
    return {
        'comment_id': [not_missing, unicode, issue_comment_exists],
    }


def issue_dataset_controller_schema():
    return {
        'status': [ignore_missing, unicode],
        'sort': [ignore_missing, unicode],
        'page': [ignore_missing, is_positive_integer],
        'per_page': [ignore_missing, is_positive_integer],
        'q': [ignore_missing, unicode],
        'visibility': [ignore_missing, unicode],
        'abuse_status': [ignore_missing, unicode],
    }


def issue_show_controller_schema():
    return {
        'dataset_id': [not_missing, unicode, package_exists, as_package_id],
        'issue_number': [not_missing, is_positive_integer],
        '__after': [issue_number_exists_for_dataset],
    }


def organization_users_autocomplete_schema():
    return {
        'q': [not_missing, unicode],
        'organization_id': [not_missing, unicode],
        'limit': [ignore_missing, is_positive_integer],
    }
