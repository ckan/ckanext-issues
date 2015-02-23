from ckan.lib import search
from ckan.new_tests import factories, helpers
from ckan.plugins import toolkit

from ckanext.issues.tests import factories as issue_factories

from nose.tools import assert_equals, assert_raises


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


class TestIssueList(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_list_all_issues_for_dataset(self):
        user = factories.User()
        dataset = factories.Dataset()

        [issue_factories.Issue(user=user, user_id=user['id'],
                               dataset_id=dataset['id'], description=i)
            for i in range(0, 10)]
        issues_list = helpers.call_action('issue_list',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='ascending')
        assert_equals(range(1, 11), [i['id'] for i in issues_list])

    def test_list_all_issues_for_dataset_without_dataset_id_fails(self):
        user = factories.User()
        assert_raises(
            toolkit.ValidationError,
            helpers.call_action,
            'issue_list',
            context={'user': user['name']})

    def test_limit(self):
        user = factories.User()
        dataset = factories.Dataset()

        [issue_factories.Issue(user=user, user_id=user['id'],
                               dataset_id=dataset['id'], description=i)
            for i in range(0, 10)]
        issues_list = helpers.call_action('issue_list',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='ascending',
                                          limit=5)
        assert_equals(range(1, 6), [i['id'] for i in issues_list])

    def test_offset(self):
        user = factories.User()
        dataset = factories.Dataset()

        [issue_factories.Issue(user=user, user_id=user['id'],
                               dataset_id=dataset['id'], description=i)
            for i in range(0, 10)]
        issues_list = helpers.call_action('issue_list',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='ascending',
                                          offset=5)
        assert_equals(range(6, 11), [i['id'] for i in issues_list])

    def test_pagination(self):
        user = factories.User()
        dataset = factories.Dataset()

        [issue_factories.Issue(user=user, user_id=user['id'],
                               dataset_id=dataset['id'], description=i)
            for i in range(0, 10)]
        issues_list = helpers.call_action('issue_list',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='ascending',
                                          offset=5,
                                          limit=3)
        assert_equals(range(6, 9), [i['id'] for i in issues_list])
