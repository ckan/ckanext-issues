from ckan.plugins import toolkit
from ckan import model as cmodel
from ckanext.issues import model
from ckanext.issues.logic import schema


def show(issue_id, dataset_id, session):
    issue_id = _validate_show(issue_id, dataset_id, session)
    issue = toolkit.get_action('issue_show')(data_dict={'id': issue_id})
    issueobj = model.Issue.get(issue_id)

    issue['comment'] = issue['description'] or toolkit._(
        'No description provided')
    comment_count = len(issueobj.comments)

    issue['assignee'] = _get_assigned_user(issue['assignee_id'])

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


def _get_assigned_user(assignee_id):
    try:
        return toolkit.get_action('user_show')(data_dict={'id': assignee_id})
    except toolkit.ObjectNotFound:
        return None
