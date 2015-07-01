import logging
from datetime import datetime

import ckan.logic as logic
import ckan.plugins as p
import ckan.model as model
from ckan.logic import validate
import ckanext.issues.model as issuemodel
from ckanext.issues.logic import schema
try:
    import ckan.authz as authz
except ImportError:
    import ckan.new_authz as authz

from pylons import config

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


@validate(schema.issue_create_schema)
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
    p.toolkit.check_access('issue_create', context, data_dict)

    user = context['user']
    user_obj = model.User.get(user)
    data_dict['user_id'] = user_obj.id

    dataset = model.Package.get(data_dict['dataset_id'])
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
    validated_data_dict, errors = p.toolkit.navl_validate(
        data_dict,
        schema.issue_update_schema(),
        context
    )
    if errors:
        raise p.toolkit.ValidationError(errors)

    # TODO:fix below to use validated_data_dict,
    #      and move validation into the schema
    session = context['session']

    issue = issuemodel.Issue.get(data_dict['id'], session=session)
    status_change = data_dict.get('status') and (data_dict.get('status') !=
                                                 issue.status)

    ignored_keys = ['id', 'created', 'user', 'dataset_id', 'spam_count',
                    'spam_state']
    for k, v in data_dict.items():
        if k not in ignored_keys:
            setattr(issue, k, v)

    if status_change:
        if data_dict['status'] == issuemodel.ISSUE_STATUS.closed:
            issue.resolved = datetime.now()
            user = context['user']
            user_dict = p.toolkit.get_action('user_show')(
                data_dict={'id': user})
            issue.assignee_id = user_dict['id']
        elif data_dict['status'] == issuemodel.ISSUE_STATUS.open:
            issue.resolved = None

    session.add(issue)
    session.commit()
    return issue.as_dict()


def issue_comment_create(context, data_dict):
    '''Add a new issue comment.

    You must provide your API key in the Authorization header.

    :param comment: the comment text
    :type comment: string
    :param issue_id: the id of the issue the comment belongs to
    :type dataset_id: integer

    :returns: the newly created issue comment
    :rtype: dictionary
    '''
    user = context['user']
    user_obj = model.User.get(user)

    issue = issuemodel.Issue.get(data_dict['issue_id'])
    if issue is None:
        raise p.toolkit.ValidationError({
            'issue_id': ['No issue exists with id %s' % data_dict['issue_id']]
        })

    auth_dict = {'dataset_id': issue.dataset_id}
    p.toolkit.check_access('issue_comment_create', context, auth_dict)

    data_dict['user_id'] = user_obj.id

    issue = issuemodel.IssueComment(**data_dict)
    model.Session.add(issue)
    model.Session.commit()

    log.debug('Created issue comment %s' % (issue.id))

    return issue.as_dict()


@p.toolkit.side_effect_free
@validate(schema.issue_search_schema)
def issue_search(context, data_dict):
    '''Search issues

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to (optional)
    :type dataset_id: string
    :param organization_id: the name or id of the organization for the datasets
        to filter the issues by (optional)
    :type organization_id: string
    :param include_sub_organizations: if filtering by organization_id, this
        includes organizations below the specified one in the hierarchy.
        (default=False)
    :type include_sub_organizations: bool
    :param q: a query string, currently on searches for titles that match
        this query
    :type q: string
    :param sort: sorting method for the results returned
    :type sort: string, must be 'newest', 'oldest', 'most_commented',
        'least_commented', 'recently_update', 'least_recently_updated'
    :param limit: number of results to return
    :type limit: int
    :param offset: offset of the search results to return
    :type offset: int
    :param spam_state: filter on spam_state
    :type spam_state: string in 'visible', 'hidden', ''
    :param include_datasets: include details of the dataset each issue is
        attached to
    :type include_datasets: bool

    :returns: list of issues
    :rtype: list of dictionaries

    '''
    p.toolkit.check_access('issue_search', context, data_dict)
    user = context['user']
    dataset_id = data_dict.get('dataset_id')
    organization_id = data_dict.get('organization_id')
    spam_state = 'visible'
    if organization_id:
        try:
            p.toolkit.check_access('organization_update', context,
                                   data_dict={'id': organization_id})
            spam_state = data_dict.get('spam_state', None)
        except p.toolkit.NotAuthorized:
            pass
    elif dataset_id:
        try:
            p.toolkit.check_access('package_update', context,
                                data_dict={'id': dataset_id})
            spam_state = data_dict.get('spam_state', None)
        except p.toolkit.NotAuthorized:
            pass
    elif authz.is_sysadmin(user):
        spam_state = data_dict.get('spam_state', None)

    data_dict['spam_state'] = spam_state
    data_dict.pop('__extras', None)
    data_dict['include_datasets'] = \
        p.toolkit.asbool(data_dict.get('include_datasets'))

    return issuemodel.Issue.get_issues(
        session=context['session'],
        **data_dict)


@validate(schema.issue_delete_schema)
def issue_delete(context, data_dict):
    '''Delete and issues

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to
    :type dataset_id: string
    :param issue_id: the id of the issue the comment belongs to
    :type issue_id: integer
    '''
    p.toolkit.check_access('issue_delete', context, data_dict)
    session = context['session']
    issue_id = data_dict['issue_id']
    issue = issuemodel.Issue.get(issue_id, session=session)
    if not issue:
        raise NotFound('{0} was not found.'.format(issue_id))
    session.delete(issue)
    session.commit()


@p.toolkit.side_effect_free
@validate(schema.organization_users_autocomplete_schema)
def organization_users_autocomplete(context, data_dict):
    session = context['session']
    user = context['user']
    q = data_dict['q']
    organization_id = data_dict['organization_id']
    limit = data_dict.get('limit', 20)
    query = session.query(model.User.id, model.User.name,
                          model.User.fullname)\
        .filter(model.Member.group_id == organization_id)\
        .filter(model.Member.table_name == 'user')\
        .filter(model.Member.capacity.in_(['editor', 'admin']))\
        .filter(model.User.state != model.State.DELETED)\
        .filter(model.User.id == model.Member.table_id)\
        .filter(model.User.name.ilike('{0}%'.format(q)))\
        .limit(limit)

    users = []
    for user in query.all():
        user_dict = dict(user.__dict__)
        user_dict.pop('_labels', None)
        users.append(user_dict)
    return users


@validate(schema.issue_report_schema)
def issue_report(context, data_dict):
    '''Report an issue

    If you are a org admin/editor, this marks the comment as spam; if you are
    any other user, this will up the spam count until it exceeds the config
    option ckanext.issues.max_strikes

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to
    :type dataset_id: string
    :param issue_id: the id of the issue the comment belongs to
    :type issue_id: integer
    '''
    p.toolkit.check_access('issue_report', context, data_dict)
    session = context['session']

    issue_id = data_dict['issue_id']
    issue = issuemodel.Issue.get(issue_id, session=session)
    try:
        # if you're an org admin/editor (can edit the dataset, it gets marked
        # as spam immediately
        dataset_id = data_dict['dataset_id']
        context = {
            'user': context['user'],
            'session': session,
            'model': model,
        }
        p.toolkit.check_access('package_update', context,
                               data_dict={'id': dataset_id})
        issue.mark_as_spam(session)
    except p.toolkit.NotAuthorized:
        issue.increase_spam_count(session)
        max_strikes = config.get('ckanext.issues.spam_max_strikes')
        if max_strikes and issue.spam_count > p.toolkit.asint(max_strikes):
            issue.mark_as_spam(session)


@validate(schema.issue_report_schema)
def issue_reset_spam_state(context, data_dict):
    '''Reset the spam status of a issue

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to
    :type dataset_id: string
    :param issue_id: the id of the issue the comment belongs to
    :type issue_id: integer
    '''
    p.toolkit.check_access('issue_reset_spam_state', context, data_dict)
    session = context['session']

    issue_id = data_dict['issue_id']
    issue = issuemodel.Issue.get(issue_id, session=session)
    issue.mark_as_not_spam(session)


@validate(schema.issue_comment_report_schema)
def issue_comment_reset_spam_state(context, data_dict):
    '''Reset the spam status of a issue_comment

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to
    :type dataset_id: string
    :param issue_comment_id: the id of the issue the comment belongs to
    :type issue_comment_id: integer
    '''
    p.toolkit.check_access('issue_reset_spam_state', context, data_dict)
    session = context['session']

    issue_comment_id = data_dict['issue_comment_id']
    issue_comment = issuemodel.IssueComment.get(issue_comment_id,
                                                session=session)
    issue_comment.mark_as_not_spam(session)


@validate(schema.issue_comment_report_schema)
def issue_comment_report(context, data_dict):
    '''Report a comment made on an issue.

    If you are a org admin/editor, this marks the comment as spam; if you are
    any other user, this will up the spam count until it exceeds the config
    option ckanext.issues.max_strikes

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to
    :type dataset_id: string
    :param issue_comment_id: the id of the issue the comment belongs to
    :type issue_comment_id: integer
    '''
    p.toolkit.check_access('issue_report', context, data_dict)
    session = context['session']

    issue_id = data_dict['issue_comment_id']
    issue_comment = issuemodel.IssueComment.get(issue_id, session=session)
    try:
        # if you're an org admin/editor (can edit the dataset, it gets marked
        # as spam immediately
        dataset_id = data_dict['dataset_id']
        package_context = {
            'user': context['user'],
            'session': session,
            'model': model,
        }
        p.toolkit.check_access('package_update', package_context,
                               data_dict={'id': dataset_id})
        issue_comment.mark_as_spam(session)
    except p.toolkit.NotAuthorized:
        issue_comment.increase_spam_count(session)
        max_strikes = config.get('ckanext.issues.spam_max_strikes')
        if max_strikes:
            if issue_comment.spam_count > p.toolkit.asint(max_strikes):
                issue_comment.mark_as_spam(session)
