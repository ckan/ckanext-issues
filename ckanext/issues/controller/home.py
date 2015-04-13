from ckan.plugins import toolkit

import ckanext.issues.model as issuemodel
from ckanext.issues.lib import util
from ckanext.issues.logic import schema
from ckanext.issues.lib.helpers import Pagination, get_issues_per_page


def home(dataset_id, get_query_dict):
    query, errors = toolkit.navl_validate(
        dict(get_query_dict),
        schema.issue_home_controller_schema()
    )
    if errors:
        raise toolkit.ValidationError(errors).error_summary
    query.pop('__extras', None)

    return _search_issues(dataset_id, **query)


def _search_issues(dataset_id, status=issuemodel.ISSUE_STATUS.open,
                   sort='newest', spam_state=None, q='', page=1,
                   per_page=get_issues_per_page()[0]):
    # use the function params to set default for our arguments to our
    # data_dict if needed
    params = locals().copy()

    # convert per_page, page parameters to api limit/offset
    limit = per_page
    offset = (page - 1) * limit
    params.pop('page', None)
    params.pop('per_page', None)
    params['offset'] = offset

    issues = toolkit.get_action('issue_search')(data_dict=params)
    issue_count = toolkit.get_action('issue_count')(data_dict=params)

    pagination = Pagination(page, limit, issue_count)

    template_variables = {
        'issues': issues,
        'status': status,
        'sort': sort,
        'q': q,
        'pagination': pagination,
    }
    if spam_state:
        template_variables['spam_state'] = spam_state
    return template_variables
