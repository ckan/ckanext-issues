from ckan.plugins import toolkit
from ckan.lib import helpers
from ckan import model as cmodel
from ckanext.issues import model
from ckanext.issues.logic import schema


def show(issue_id, dataset_id, session):
    issue_id = _validate_show(issue_id, dataset_id, session)
    issue = toolkit.get_action('issue_show')(data_dict={'id': issue_id})
    issueobj = model.Issue.get(issue_id)

    issue['comment'] = issue['description'] or toolkit._(
        'No description provided')
    issue['time_ago'] = helpers.time_ago_from_timestamp(issueobj.created)
    comment_count = len(issueobj.comments)
    for idx, comment in enumerate(issue['comments']):
        commentobj = issueobj.comments[idx]
        comment['time_ago'] = helpers.time_ago_from_timestamp(
            commentobj.created)
    return {
        'issue': issue,
        'comment_count': comment_count,
    }


def _validate_show(issue_id, dataset_id, session,
                   schema=schema.issue_show_controller_schema()):
    query, errors = toolkit.navl_validate(
        data={'id': issue_id, 'dataset_id': dataset_id}, schema=schema,
        context={'session': session, 'model': cmodel})
    if errors:
        raise toolkit.ValidationError(errors)
    return issue_id
