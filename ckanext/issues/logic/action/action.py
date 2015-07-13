import logging
from datetime import datetime

import ckan.logic as logic
import ckan.plugins as p
import ckan.model as model
from ckan.logic import validate
import ckanext.issues.model as issuemodel
from ckanext.issues.logic import schema
from ckanext.issues.exception import ReportAlreadyExists
try:
    import ckan.authz as authz
except ImportError:
    import ckan.new_authz as authz

from pylons import config
from sqlalchemy.exc import IntegrityError

NotFound = logic.NotFound
_get_or_bust = logic.get_or_bust

log = logging.getLogger(__name__)


def _add_reports(obj, can_edit, current_user):
    reports = [r.user_id for r in obj.abuse_reports]
    if can_edit:
        return reports
    else:
        user_obj = model.User.get(current_user)
        if user_obj and user_obj.id in reports:
            return [user_obj.id]
        else:
            return []


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

    user = context.get('user')
    if user:
        try:
            can_edit = p.toolkit.check_access('package_update', context,
                                            data_dict={'id': issue.dataset_id})
        except p.toolkit.NotAuthorized:
            can_edit = False
    else:
        can_edit = False

    include_reports = data_dict.get('include_reports')

    comments = []
    for comment in issue.comments:
        comment_dict = comment.as_dict()
        if include_reports:
            comment_dict['abuse_reports'] = _add_reports(comment, can_edit,
                                                         context['user'])
        comments.append(comment_dict)

    issue_dict['comments'] = comments

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

    ignored_keys = ['id', 'created', 'user', 'dataset_id', 'spam_state']
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
    can_update = False
    if organization_id:
        try:
            p.toolkit.check_access('organization_update', context,
                                   data_dict={'id': organization_id})
            spam_state = data_dict.get('spam_state', None)
            can_update = True
        except p.toolkit.NotAuthorized:
            pass
    elif dataset_id:
        try:
            p.toolkit.check_access('package_update', context,
                                   data_dict={'id': dataset_id})
            spam_state = data_dict.get('spam_state', None)
            can_update = True
        except p.toolkit.NotAuthorized:
            pass
    elif authz.is_sysadmin(user):
        spam_state = data_dict.get('spam_state', None)
        can_update = True

    data_dict['spam_state'] = spam_state
    data_dict.pop('__extras', None)
    include_datasets = p.toolkit.asbool(data_dict.get('include_datasets'))
    include_reports = p.toolkit.asbool(data_dict.get('include_reports'))
    data_dict['include_datasets'] = include_datasets

    query = issuemodel.Issue.get_issues(
        session=context['session'],
        **data_dict)

    count = query.count()
    results = [issue.as_plain_dict(u, comment_count_, updated,
                                   include_dataset=include_datasets,
                                   include_reports=include_reports)
               for (issue, u, comment_count_, updated) in query.all()]

    if include_reports and not can_update:
        user_obj = model.User.get(user)
        if user_obj:
            results = _filter_reports_for_user(user_obj.id, results)

    return {
        'count': count,
        'results': results,
    }


def _filter_reports_for_user(user_id, results):
    '''Filter the abuse reports

    If the user does not have update permissions on the dataset, then they will
    only be able to see reports that they have made, this function filters out
    any reports made by other users
    '''
    for result in results:
        if result.get('abuse_reports'):
            if user_id in result['abuse_reports']:
                result['abuse_reports'] = [user_id]
            else:
                result['abuse_reports'] = []
    return results


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
    user_obj = model.User.get(context['user'])
    #session.begin_nested()
    try:
        issue.report_abuse(session, user_obj.id)
    except IntegrityError:
        session.rollback()
        raise ReportAlreadyExists(
            p.toolkit._('Issue has already been reported by this user')
        )
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

        issue.change_visiblity(session, u'hidden')
    except p.toolkit.NotAuthorized:
        max_strikes = config.get('ckanext.issues.max_strikes')
        if max_strikes and len(issue.abuse_reports) >= p.toolkit.asint(max_strikes):
            issue.change_visiblity(session, u'hidden')
    session.commit()


@validate(schema.issue_report_schema)
def issue_report_clear(context, data_dict):
    '''Clears the reports on issue

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to
    :type dataset_id: string
    :param issue_id: the id of the issue the comment belongs to
    :type issue_id: integer
    '''
    p.toolkit.check_access('issue_report_clear', context, data_dict)
    session = context['session']

    issue_id = data_dict['issue_id']
    issue = issuemodel.Issue.get(issue_id, session=session)

    user = context['user']
    user_obj = model.User.get(user)
    user_id = user_obj.id
    try:
        dataset_id = data_dict['dataset_id']
        package_context = {
            'user': context['user'],
            'session': session,
            'model': model,
        }
        p.toolkit.check_access('package_update', package_context,
                               data_dict={'id': dataset_id})
        issue.clear_all_abuse_reports(session)
    except p.toolkit.NotAuthorized:
        issue.clear_abuse_report(session, user_id)
        max_strikes = config.get('ckanext.issues.max_strikes')
        if max_strikes and len(issue.abuse_reports) <= p.toolkit.asint(max_strikes):
            issue.change_visiblity(session, u'visible')
    session.commit()
    return True


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
    user_obj = model.User.get(context['user'])
    try:
        issue_comment.report_abuse(session, user_obj.id)
    except IntegrityError:
        session.rollback()
        raise ReportAlreadyExists(
            p.toolkit._('Comment has already been reported by this user')
        )
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
        issue_comment.change_visibility(session, u'hidden')
    except p.toolkit.NotAuthorized:
        max_strikes = config.get('ckanext.issues.max_strikes')
        if max_strikes:
            if len(issue_comment.abuse_reports) > p.toolkit.asint(max_strikes):
                issue_comment.change_visibility(session, u'hidden')
    session.commit()


@validate(schema.issue_comment_report_schema)
def issue_comment_report_clear(context, data_dict):
    '''Clear the reports on an comment

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to
    :type dataset_id: string
    :param issue_comment_id: the id of the issue the comment belongs to
    :type issue_comment_id: integer
    '''
    p.toolkit.check_access('issue_report_clear', context, data_dict)
    session = context['session']

    issue_comment_id = data_dict['issue_comment_id']
    issue_comment = issuemodel.IssueComment.get(issue_comment_id,
                                                session=session)
    user = context['user']
    user_obj = model.User.get(user)
    user_id = user_obj.id
    try:
        dataset_id = data_dict['dataset_id']
        package_context = {
            'user': context['user'],
            'session': session,
            'model': model,
        }
        p.toolkit.check_access('package_update', package_context,
                               data_dict={'id': dataset_id})
        issue_comment.clear_all_abuse_reports(session)
    except p.toolkit.NotAuthorized:
        issue_comment.clear_abuse_report(session, user_id)
        max_strikes = config.get('ckanext.issues.max_strikes')
        if (max_strikes and
           len(issue_comment.abuse_reports) <= p.toolkit.asint(max_strikes)):
            issue_comment.change_visibility(session, u'visible')
    session.commit()
    return True


@validate(schema.issue_report_schema)
def issue_report_show(context, data_dict):
    '''Fetch the absuse reports for an issue

    If you are a package owner, this returns the full list of users that have
    reported this issue, otherwise it will return whether the user has marked
    the issue as abuse

    :param dataset_id: the name or id of the dataset that the issue item
        belongs to
    :type dataset_id: string
    :param issue_id: the id of the issue the comment belongs to
    :type issue_id: integer
    '''
    p.toolkit.check_access('issue_report', context, data_dict)
    session = context['session']

    issue_id = data_dict['issue_id']
    user = context['user']
    user_obj = model.User.get(user)
    user_id = user_obj.id

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
        reports = issuemodel.IssueReport.get_reports(session, issue_id)
    except p.toolkit.NotAuthorized:
        reports = issuemodel.IssueReport.get_reports_for_user(session, user_id,
                                                              issue_id)
    return [i.user_id for i in reports]
