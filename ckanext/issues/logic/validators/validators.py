from ckan.plugins import toolkit
from ckanext.issues import model as issuemodel


def is_valid_status(value, context):
    if value in issuemodel.ISSUE_STATUS:
        return value
    else:
        raise toolkit.Invalid(toolkit._(
            '{0} is not a valid status'.format(value))
        )


def is_valid_sort(filter_string, context):
    try:
        return issuemodel.IssueFilter[filter_string]
    except KeyError:
        msg_str = 'Cannot apply filter. "{0}" is not a valid filter'
        raise toolkit.Invalid(
            toolkit._(msg_str.format(filter_string))
        )


def as_package_id(package_id_or_name, context):
    '''given a package_id_or_name, return just the package id'''
    model = context['model']
    return model.Package.get(package_id_or_name).id


def issue_exists(issue_id, context):
    result = issuemodel.Issue.get(issue_id, session=context['session'])
    if not result:
        raise toolkit.Invalid(toolkit._('Issue not found') + ': %s' % issue_id)
    return issue_id
