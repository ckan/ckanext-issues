import logging

import pylons
import sqlalchemy

import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.plugins as p
import ckan.model.meta as meta
import ckanext.datastore.logic.schema as dsschema
from ckanext.issues import model

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
    issue = model.Issue.get(id)
    context['issue'] = issue
    if issue is None:
        raise NotFound
    # _check_access('issue_show', context, data_dict)

    issue_dict = issue.as_dict()
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

    # TODO: not working - getting a 409 ...
    # p.toolkit.check_access('issue_create', context, data_dict)

    data_dict["creator_id"] = userobj.id
    #data, errors = _validate(
    #    data_dict, ckan.logic.schema.default_related_schema(), context)
    #if errors:
    #    model.Session.rollback()
    #    raise ValidationError(errors)
    dataset = model.Package.get(data_dict['dataset'])
    del data_dict['dataset']

    try:
        issue = model.Issue(**data_dict)
        issue.dataset = dataset
        meta.Session.add(issue)
        meta.Session.commit()
    except Exception as e:
        log.warn("Database Error: " + str(e))
        meta.Session.rollback()
        raise e
    meta.Session.remove()

    log.debug('Created issue %s (%s)' % (issue.title, issue.id))
    return issue.as_dict()

