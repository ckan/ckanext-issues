from ckan import model
from ckan.lib import search
from ckan.new_tests import factories, helpers

from ckanext.issues.tests import factories as issue_factories

from nose.tools import assert_equals

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
