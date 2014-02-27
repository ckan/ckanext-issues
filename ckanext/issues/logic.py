import logging

from datetime import datetime
import pylons
import sqlalchemy

import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.plugins as p
import ckan.model.meta as meta
import ckanext.datastore.logic.schema as dsschema
import ckan.model as model
import ckanext.issues.model as issuemodel

NotFound = logic.NotFound
_get_or_bust = logic.get_or_bust

log = logging.getLogger(__name__)

def issue_show(context, data_dict=None):
    '''Return a single issue.

    :param id: the id of the issue to show
    :type id: string

    :rtype: dictionary
    '''
    id = _get_or_bust(data_dict, 'id')
    issue = issuemodel.Issue.get(id)
    context['issue'] = issue
    if issue is None:
        raise NotFound
    issue_dict = issue.as_dict()
    p.toolkit.check_access('issue_show', context, issue_dict)
    return issue_dict

def issue_create(context, data_dict):
    '''Add a new issue.

    You must provide your API key in the Authorization header.

    :param title: the title of the issue
    :type title: string
    :param description: the description of the issue item (optional)
    :type description: string
    :param dataset_id: the name or id of the dataset that the issue item
        belongs to (optional)
    :type dataset_id: string

    :returns: the newly created issue item
    :rtype: dictionary
    '''
    userobj = context['auth_user_obj']

    p.toolkit.check_access('issue_create', context, data_dict)

    data_dict["user_id"] = userobj.id
    #data, errors = _validate(
    #    data_dict, ckan.logic.schema.default_related_schema(), context)
    #if errors:
    #    model.Session.rollback()
    #    raise ValidationError(errors)
    dataset = model.Package.get(data_dict['dataset_id'])
    # TODO propoer validation?
    if dataset is None:
        raise p.toolkit.ValidationError({
            'dataset_id': ['No dataset exists with id %s' % data_dict['dataset_id']]
        })
    del data_dict['dataset_id']

    issue = issuemodel.Issue(**data_dict)
    issue.dataset = dataset
    model.Session.add(issue)
    model.Session.commit()

    log.debug('Created issue %s (%s)' % (issue.title, issue.id))
    return issue.as_dict()

def issue_update(context, data_dict):
    '''Update an issue.

    You must provide your API key in the Authorization header.

    :param title: the title of the issue
    :type title: string
    :param description: the description of the issue item (optional)
    :type description: string
    :param dataset_id: the name or id of the dataset that the issue item
        belongs to (optional)
    :type dataset_id: string

    :returns: the newly updated issue item
    :rtype: dictionary
    '''
    p.toolkit.check_access('issue_update', context, data_dict)
    issue = issuemodel.Issue.get(data_dict['id'])
    status_change = data_dict['status'] and (data_dict['status'] !=
            issue.status)
    for k,v in [(k,v) for k,v in data_dict.items() if k not in ['id', 'created', 'user']]:
        setattr(issue, k, v)

    if status_change:
        if data_dict['status'] == issuemodel.ISSUE_STATUS.closed:
            issue.resolved = datetime.now()
            issue.resolver_id = context['auth_user_obj'].id
        elif data_dict['status'] == issuemodel.ISSUE_STATUS.open:
            issue.resolved = None
            issue.resolver = None

    model.Session.add(issue)
    model.Session.commit()
    return issue.as_dict()

def issue_comment_create(context, data_dict):
    '''Add a new issue comment.

    You must provide your API key in the Authorization header.

    :param description: the description of the issue item
    :type description: string
    :param issue_id: the id of the issue the comment belongs to
    :type dataset_id: integer

    :returns: the newly created issue comment
    :rtype: dictionary
    '''
    userobj = context['auth_user_obj']

    issue = issuemodel.Issue.get(data_dict['issue_id'])
    if issue is None:
        raise p.toolkit.ValidationError({
            'issue_id': ['No issue exists with id %s' % data_dict['issue_id']]
        })

    auth_dict = {
        'dataset_id': issue.dataset_id
        }
    p.toolkit.check_access('issue_comment_create', context, auth_dict)

    data_dict["user_id"] = userobj.id

    issue = issuemodel.IssueComment(**data_dict)
    model.Session.add(issue)
    model.Session.commit()

    log.debug('Created issue comment %s' % (issue.id))

    return issue.as_dict()

