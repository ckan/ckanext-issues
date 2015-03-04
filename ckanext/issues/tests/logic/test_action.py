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

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='oldest')
        assert_equals([i['id'] for i in created_issues],
                      [i['id'] for i in issues_list])

    def test_list_all_issues_for_dataset_without_dataset_id_fails(self):
        user = factories.User()
        assert_raises(
            toolkit.ValidationError,
            helpers.call_action,
            'issue_search',
            context={'user': user['name']})

    def test_limit(self):
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
                                          limit=5)
        assert_equals([i['id'] for i in created_issues][:5],
                      [i['id'] for i in issues_list])

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
                                          offset=5)
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
                                          limit=3)
        assert_equals([i['id'] for i in created_issues][5:8],
                      [i['id'] for i in issues_list])

    def test_filter_newest(self):
        user = factories.User()
        dataset = factories.Dataset()

        [issue_factories.Issue(user=user, user_id=user['id'],
                               dataset_id=dataset['id'], description=i)
            for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='newest')
        assert_equals(list(reversed(range(1, 11))),
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
                                          sort='least_commented')
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
                                          sort='most_commented')
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
                                              q='title')

        expected_issue_ids = [i['id'] for i in issues[:2]]
        assert_equals(expected_issue_ids, [i['id'] for i in filtered_issues])


class TestIssueUpdate(object):
    def teardown(object):
        helpers.reset_db()

    def test_reopen_an_issue(object):
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
