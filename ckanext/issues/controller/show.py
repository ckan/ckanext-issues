from ckan.plugins import toolkit
from ckan import model as cmodel
from ckanext.issues import model
from ckanext.issues.logic import schema


def show(issue_number, dataset_id, session):
    validated_data_dict = _validate_show(issue_number, dataset_id, session)
    dataset_id = validated_data_dict['dataset_id']
    issue = toolkit.get_action('issue_show')(
        data_dict={
            'issue_number': issue_number,
            'dataset_id': dataset_id,
            'include_reports': True,
        }
    )

    issue['comment'] = issue['description'] or toolkit._(
        'No description provided')

    issue['assignee'] = _get_assigned_user(issue['assignee_id'], session)

    try:
        reports = toolkit.get_action('issue_report_show')(
            data_dict={
                'issue_number': issue_number,
                'dataset_id': dataset_id,
            }
        )
        issue['abuse_reports'] = reports
    except toolkit.NotAuthorized:
        pass

    issue_obj = model.Issue.get_by_number(dataset_id, issue_number, session)
    comment_count = len(issue_obj.comments)
    return {
        'issue': issue,
        'comment_count': comment_count,
    }


def _validate_show(issue_number, dataset_id, session,
                   schema=schema.issue_show_controller_schema()):
    query, errors = toolkit.navl_validate(
        data={'issue_number': issue_number, 'dataset_id': dataset_id},
        schema=schema,
        context={'session': session, 'model': cmodel})
    if errors:
        raise toolkit.ValidationError(errors)
    return query


def _get_assigned_user(assignee_id, session):
    context = {'session': session, 'model': cmodel}
    data_dict = {'id': assignee_id}
    # we only need the basic properties of the user, not its datasets etc
    if toolkit.check_ckan_version(min_version='2.3'):
        # these are the defaults, but just in case...
        data_dict.update({'include_datasets': False,
                          'include_num_followers': False})
    else:
        context = {'return_minimal': True}
    try:
        return toolkit.get_action('user_show')(context, data_dict)
    except toolkit.ObjectNotFound:
        return None
    except toolkit.NotAuthorized:
        return None
