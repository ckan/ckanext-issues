from ckan.plugins import toolkit

import ckanext.issues.model as issuemodel
from ckanext.issues.lib import util
from ckanext.issues.logic import schema
from ckanext.issues.lib.helpers import Pagination, get_issues_per_page


def home(dataset_id, get_query_dict):
    status, sort, page, per_page, q = _validate_home(get_query_dict)
    issues, pagination = _search_issues(dataset_id, status, sort, q,
        page, per_page)
    return {
        'issues': issues,
        'status': status,
        'sort': sort,
        'q': q,
        'pagination': pagination,
    }


def _search_issues(dataset_id, status, sort, q=None, page=1, per_page=15):
    def _add_time_since(issue):
        issue['created_time_ago'] = util.time_ago(issue['created'])
        return issue

    offset = (page - 1) * per_page
    issues = toolkit.get_action('issue_search')(
        data_dict={
            'dataset_id': dataset_id,
            'status': status,
            'sort': sort,
            'offset': offset,
            'limit': per_page,
            'q': q,
        }
    )

    issues = map(_add_time_since, issues)

    issue_count = toolkit.get_action('issue_count')(
        data_dict={
            'dataset_id': dataset_id,
            'status': status,
            'q': q,
        }
    )
    pagination = Pagination(page, per_page, issue_count)
    return issues, pagination


def _validate_home(get_query_dict, 
                   schema=schema.issue_home_controller_schema()):
    query, errors = toolkit.navl_validate(dict(get_query_dict), schema)
    if errors:
        raise toolkit.ValidationError(errors).error_summary

    status = query.get('status', issuemodel.ISSUE_STATUS.open)
    sort = query.get('sort')
    if not sort:
        sort = 'newest'

    page = query.get('page', 1)
    issues_per_page = get_issues_per_page()
    per_page = query.get('per_page', issues_per_page[0])
    q = query.get('q', '')
    return status, sort, page, per_page, q
