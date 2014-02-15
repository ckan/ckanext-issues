import logging

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
    '''Add a new issue for a dataset.

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
    session = context['session']
    user = context['user']
    userobj = model.User.get(user)

    p.toolkit.check_access('issue_create', context, data_dict)

    data_dict["creator_id"] = userobj.id
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
    model.repo.commit_and_remove()

    log.debug('Created issue %s (%s)' % (issue.title, issue.id))
    return issue.as_dict()

