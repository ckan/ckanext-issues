from ckan.plugins import toolkit
from ckanext.issues import model as issuemodel


is_positive_integer = toolkit.get_validator('is_positive_integer')


def is_valid_status(value, context):
    if value in issuemodel.ISSUE_STATUS:
        return value
    else:
        raise toolkit.Invalid(toolkit._(
            '{0} is not a valid status'.format(value))
        )


def is_valid_sort(filter_string, context):
    '''takes a string, validates and returns an IssueFilter enum'''
    try:
        return issuemodel.IssueFilter[filter_string]
    except KeyError:
        msg_str = 'Cannot apply filter. "{0}" is not a valid filter'
        raise toolkit.Invalid(
            toolkit._(msg_str.format(filter_string))
        )


def is_valid_abuse_status(filter_string, context):
    '''takes a string, validates and returns an AbuseStatus enum'''
    try:
        return issuemodel.AbuseStatus[filter_string]
    except KeyError:
        msg_str = 'Cannot apply filter. "{0}" is not a valid abuse status'
        raise toolkit.Invalid(
            toolkit._(msg_str.format(filter_string))
        )


def as_package_id(package_id_or_name, context):
    '''given a package_id_or_name, return just the package id'''
    model = context['model']
    package = model.Package.get(package_id_or_name)
    if not package:
        raise toolkit.Invalid('%s: %s' % (toolkit._('Not found'),
                                          toolkit._('Dataset')))
    else:
        return package.id


def as_org_id(org_id_or_name, context):
    '''given a org_id_or_name, return just the org id'''
    model = context['model']
    org = model.Group.get(org_id_or_name)
    if not org:
        raise toolkit.Invalid('%s: %s' % (toolkit._('Not found'),
                                          toolkit._('Organization')))
    else:
        return org.id


def issue_exists(issue_id, context):
    issue_id = is_positive_integer(issue_id, context)
    result = issuemodel.Issue.get(issue_id, session=context['session'])
    if not result:
        raise toolkit.Invalid(toolkit._('Issue not found') + ': %s' % issue_id)
    return issue_id


def issue_number_exists_for_dataset(key, data, errors, context):
    # do not run this validator unless we passed the initial validation
    if not (errors['dataset_id', ] or errors['issue_number', ]):
        session = context['session']
        dataset_id = data.get(('dataset_id',))
        issue_number = data.get(('issue_number',))
        issue = issuemodel.Issue.get_by_number(dataset_id, issue_number,
                                               session)
        if not issue:
            raise toolkit.ObjectNotFound(toolkit._('Issue not found'))


def issue_comment_exists(issue_comment_id, context):
    issue_comment_id = is_positive_integer(issue_comment_id, context)
    result = issuemodel.IssueComment.get(issue_comment_id,
                                         session=context['session'])
    if not result:
        raise toolkit.Invalid(
            toolkit._('Issue Comment not found') + ': %s' % issue_comment_id
        )
    return issue_comment_id
