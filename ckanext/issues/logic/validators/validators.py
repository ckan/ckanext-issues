from ckan.plugins import toolkit
from ckanext.issues import model


def is_valid_status(value, context):
    if value in model.ISSUE_STATUS:
        return value
    else:
        raise toolkit.Invalid(toolkit._(
            '{0} is not a valid status'.format(value))
        )


def is_valid_sort(filter_string, context):
    try:
        return model.IssueFilter[filter_string]
    except KeyError:
        msg_str = 'Cannot apply filter. "{0}" is not a valid filter'
        raise toolkit.Invalid(
            toolkit._(msg_str.format(filter_string))
        )


def as_package_id(package_id_or_name, context):
    '''given a package_id_or_name, return just the package id'''
    model = context['model']
    return model.Package.get(package_id_or_name).id
