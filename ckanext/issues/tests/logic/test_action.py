from ckan import model
from ckan.lib import search
try:
    from ckan.tests import factories, helpers
except ImportError:
    from ckan.new_tests import factories, helpers
from ckan.plugins import toolkit

from ckanext.issues.model import Issue
from ckanext.issues.tests import factories as issue_factories

from nose.tools import assert_equals, assert_raises
import mock


class TestIssue(object):
    def setup(self):
        self.user = factories.User()
        self.dataset = factories.Dataset()

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_issue_create(self):
        issue_create_result = toolkit.get_action('issue_create')(
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': self.dataset['id'],
            }
        )

        issue_object = Issue.get(issue_create_result['id'])
        assert_equals('Title', issue_object.title)
        assert_equals('Description', issue_object.description)

    def test_issue_create_dataset_does_not_exist(self):
        issue_create = toolkit.get_action('issue_create')
        assert_raises(
            toolkit.ValidationError,
            issue_create,
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': 'nonsense',
            }
        )

    def test_issue_create_test_validation(self):
        issue_create = toolkit.get_action('issue_create')
        assert_raises(
            toolkit.ValidationError,
            issue_create,
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': 'not a datasest',
            }
        )

    def test_issue_create_cannot_set_spam(self):
        issue_create_result = toolkit.get_action('issue_create')(
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': self.dataset['id'],
                'spam_state': 'hidden'
            }
        )
        issue_object = Issue.get(issue_create_result['id'])
        assert_equals('visible', issue_object.spam_state)


class TestIssueComment(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_create_comment_on_issue(self):
        user = factories.User()
        dataset = factories.Dataset()

        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        helpers.call_action('issue_comment_create',
                            context={'user': user['name']},
                            issue_id=issue['id'], comment='some comment')

        result = helpers.call_action('issue_show',
                                     context={'user': user['name']},
                                     id=issue['id'])
        comments = result['comments']
        assert_equals(len(comments), 1)
        assert_equals(comments[0]['comment'], 'some comment')

    def test_create_comment_on_closed_issue(self):
        user = factories.User()
        dataset = factories.Dataset()

        # create and close our issue
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        closed = helpers.call_action('issue_update', id=issue['id'],
                                     context={'user': user['name']},
                                     status='closed')
        assert_equals('closed', closed['status'])

        # check we can comment on closed issues
        helpers.call_action('issue_comment_create',
                            context={'user': user['name']},
                            issue_id=issue['id'], comment='some comment')

        result = helpers.call_action('issue_show',
                                     context={'user': user['name']},
                                     id=issue['id'])
        comments = result['comments']
        assert_equals(len(comments), 1)
        assert_equals(comments[0]['comment'], 'some comment')


class TestIssueSearch(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_list_all_issues_for_dataset(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        search_res = helpers.call_action('issue_search',
                                         context={'user': user['name']},
                                         dataset_id=dataset['id'],
                                         sort='oldest')
        issues_list = search_res['results']
        assert_equals([i['id'] for i in created_issues],
                      [i['id'] for i in issues_list])
        assert_equals(search_res['count'], 10)

    def test_list_all_issues_for_organization(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'])

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          organization_id=org['id'],
                                          sort='oldest')['results']
        assert_equals([i['id'] for i in created_issues],
                      [i['id'] for i in issues_list])

    def test_list_all_issues(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          sort='oldest')['results']
        assert_equals([i['id'] for i in created_issues],
                      [i['id'] for i in issues_list])

    def test_limit(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        search_res = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='oldest',
                                          limit=5)
        issues_list = search_res['results']
        assert_equals([i['id'] for i in created_issues][:5],
                      [i['id'] for i in issues_list])
        assert_equals(search_res['count'], 10)

    def test_offset(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='oldest',
                                          offset=5)['results']
        assert_equals([i['id'] for i in created_issues][5:],
                      [i['id'] for i in issues_list])

    def test_pagination(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='oldest',
                                          offset=5,
                                          limit=3)['results']
        assert_equals([i['id'] for i in created_issues][5:8],
                      [i['id'] for i in issues_list])

    def test_filter_newest(self):
        user = factories.User()
        dataset = factories.Dataset()

        issues = [issue_factories.Issue(user=user, user_id=user['id'],
                               dataset_id=dataset['id'], description=i)
                  for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='newest')['results']
        assert_equals(list(reversed([i['id'] for i in issues])),
                      [i['id'] for i in issues_list])

    def test_filter_least_commented(self):
        user = factories.User()
        dataset = factories.Dataset()

        # issue#1 has 3 comment. #2 has 1 comments, etc
        comment_count = [3, 1, 2]
        issue_ids = []
        for i in comment_count:
            issue = issue_factories.Issue(user_id=user['id'],
                                          dataset_id=dataset['id'],
                                          description=i)
            issue_ids.append(issue['id'])

            for j in range(0, i):
                issue_factories.IssueComment(user_id=user['id'],
                                             issue_id=issue['id'])
        reordered_ids = [issue_ids[1], issue_ids[2], issue_ids[0]]

        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='least_commented')['results']
        assert_equals(reordered_ids, [i['id'] for i in issues_list])
        assert_equals([1, 2, 3], [i['comment_count'] for i in issues_list])

    def test_filter_most_commented(self):
        user = factories.User()
        dataset = factories.Dataset()

        # issue#1 has 3 comment. #2 has 1 comments, etc
        comment_count = [3, 1, 2, 0]
        issue_ids = []
        for i in comment_count:
            issue = issue_factories.Issue(user_id=user['id'],
                                          dataset_id=dataset['id'],
                                          description=i)
            issue_ids.append(issue['id'])

            for j in range(0, i):
                issue_factories.IssueComment(user_id=user['id'],
                                             issue_id=issue['id'])

        reordered_ids = [issue_ids[0], issue_ids[2], issue_ids[1],
                         issue_ids[3]]

        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='most_commented')['results']
        assert_equals(reordered_ids, [i['id'] for i in issues_list])
        assert_equals([3, 2, 1, 0], [i['comment_count'] for i in issues_list])

    def test_filter_by_title_string_search(self):
        user = factories.User()
        dataset = factories.Dataset()

        issues = [issue_factories.Issue(user_id=user['id'],
                                        dataset_id=dataset['id'],
                                        title=title)
                  for title in ['some title', 'another Title', 'issue']]

        filtered_issues = helpers.call_action('issue_search',
                                              context={'user': user['name']},
                                              dataset_id=dataset['id'],
                                              q='title')['results']

        expected_issue_ids = [i['id'] for i in issues[:2]]
        assert_equals(expected_issue_ids, [i['id'] for i in filtered_issues])


class TestIssueUpdate(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_reopen_an_issue(self):
        '''This test is resolve a bug where updating/reopening an issue
        deletes it. Magical'''
        user = factories.User()
        dataset = factories.Dataset()
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        closed = helpers.call_action('issue_update',
                                     context={'user': user['name']},
                                     id=issue['id'], status='closed')

        assert_equals('closed', closed['status'])

        after_closed = helpers.call_action('issue_show',
                                           context={'user': user['name']},
                                           id=issue['id'])
        assert_equals('closed', after_closed['status'])

        helpers.call_action('issue_update',
                            context={'user': user['name']},
                            id=issue['id'], status='open')

        reopened = helpers.call_action('issue_show',
                                       context={'user': user['name']},
                                       id=issue['id'])
        assert_equals('open', reopened['status'])

    def test_cannot_update_spam_using_update(self):
        '''we don't want users to be able to set their own spam status/count'''
        user = factories.User()
        dataset = factories.Dataset()
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])
        spam = helpers.call_action('issue_update',
                                   context={'user': user['name']},
                                   id=issue['id'], spam_state='hidden')

        after_update = helpers.call_action('issue_show',
                                           context={'user': user['name']},
                                           id=issue['id'])
        assert_equals('visible', after_update['spam_state'])



class TestIssueDelete(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_deletion(self):
        user = factories.User()
        dataset = factories.Dataset()
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        helpers.call_action('issue_delete',
                            context={'user': user['name']},
                            dataset_id=dataset['id'],
                            issue_id=issue['id'])

        assert_raises(toolkit.ObjectNotFound,
                      helpers.call_action,
                      'issue_show',
                      dataset_id=dataset['id'],
                      id=issue['id'])

    def test_delete_nonexistent_issue_raises_not_found(self):
        user = factories.User()
        dataset = factories.Dataset()
        assert_raises(toolkit.ValidationError,
                      helpers.call_action,
                      'issue_delete',
                      context={'user': user['name']},
                      dataset_id=dataset['id'],
                      issue_id='2')

    def test_delete_non_integer_parameter_issue_raises_not_found(self):
        '''issue ids are a postgres seqeunce currently'''
        user = factories.User()
        dataset = factories.Dataset()
        assert_raises(toolkit.ValidationError,
                      helpers.call_action,
                      'issue_delete',
                      context={'user': user['name']},
                      dataset_id=dataset['id'],
                      issue_id='huh')


class TestOrganizationUsersAutocomplete(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_fetch_org_editors(self):
        owner = factories.User(name='test_owner')
        editor = factories.User(name='test_editor')
        admin = factories.User(name='test_admin')
        member = factories.User(name='test_member')
        factories.User(name='test_user')
        organization = factories.Organization(user=owner, users=[
            {'name': editor['id'], 'capacity': 'editor'},
            {'name': admin['id'], 'capacity': 'admin'},
            {'name': member['id']}, ])

        result = helpers.call_action('organization_users_autocomplete',
                                     q='test',
                                     organization_id=organization['id'])
        assert_equals(
            set(['test_owner', 'test_editor', 'test_admin']),
            set([i['name'] for i in result])
        )


class TestReportAnIssue(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_increase_spam(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])

        user = factories.User(name='unauthed')
        context = {
            'user': user['name'],
            'model': model,
        }
        helpers.call_action('issue_report', context=context,
                            dataset_id=dataset['id'], issue_id=issue['id'])

        result = helpers.call_action('issue_show', id=issue['id'])
        assert_equals(1, result['spam_count'])

    def test_publisher_mark_spam(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=owner, user_id=owner['id'],
                                      dataset_id=dataset['id'])

        context = {
            'user': owner['name'],
            'model': model,
        }
        helpers.call_action('issue_report', context=context,
                            dataset_id=dataset['id'], issue_id=issue['id'])

        result = helpers.call_action('issue_show', id=issue['id'])
        assert_equals('hidden', result['spam_state'])

    @mock.patch('ckanext.issues.logic.action.action.config')
    def test_max_strikes_marks_as_spam(self, mock):
        #mock out the config value of max_strikes
        mock.get.return_value = '0'
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])

        user = factories.User(name='unauthed')
        context = {
            'user': user['name'],
            'model': model,
        }
        helpers.call_action('issue_report', context=context,
                            dataset_id=dataset['id'], issue_id=issue['id'])

        result = helpers.call_action('issue_show', id=issue['id'])
        assert_equals(1, result['spam_count'])
        assert_equals('hidden', result['spam_state'])

    def test_reset_spam_state(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'],
                                      spam_state='hidden',
                                      spam_count='20')
        context = {
            'user': owner['name'],
            'model': model,
        }
        helpers.call_action('issue_reset_spam_state', context=context,
                            dataset_id=dataset['id'], issue_id=issue['id'])
        result = helpers.call_action('issue_show', id=issue['id'])
        assert_equals(0, result['spam_count'])
        assert_equals('visible', result['spam_state'])

class TestReportCommentSpam(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_increase_spam(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])
        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               issue_id=issue['id'])


        user = factories.User(name='unauthed')
        context = {
            'user': user['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_report', context=context,
                            dataset_id=dataset['id'],
                            issue_comment_id=comment['id'])
        result = helpers.call_action('issue_show', id=issue['id'])

        assert_equals(1, result['comments'][0]['spam_count'])

    def test_publisher_mark_spam(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=owner, user_id=owner['id'],
                                      dataset_id=dataset['id'])

        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               issue_id=issue['id'])

        context = {
            'user': owner['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_report', context=context,
                            dataset_id=dataset['id'],
                            issue_comment_id=comment['id'])

        result = helpers.call_action('issue_show', id=issue['id'])
        assert_equals('hidden', result['comments'][0]['spam_state'])

    @mock.patch('ckanext.issues.logic.action.action.config')
    def test_max_strikes_marks_as_spam(self, mock):
        #mock out the config value of max_strikes
        mock.get.return_value = '0'

        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])
        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               issue_id=issue['id'])


        user = factories.User(name='unauthed')
        context = {
            'user': user['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_report', context=context,
                            dataset_id=dataset['id'],
                            issue_comment_id=comment['id'])
        result = helpers.call_action('issue_show', id=issue['id'])
        assert_equals(1, result['comments'][0]['spam_count'])
        assert_equals('hidden', result['comments'][0]['spam_state'])

    def test_reset_spam_state(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])
        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               issue_id=issue['id'],
                                               spam_state='hidden',
                                               spam_count='20')
        context = {
            'user': owner['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_reset_spam_state', context=context,
                            dataset_id=dataset['id'],
                            issue_comment_id=comment['id'])
        result = helpers.call_action('issue_show', id=issue['id'])
        assert_equals(0, result['comments'][0]['spam_count'])
        assert_equals('visible', result['comments'][0]['spam_state'])
