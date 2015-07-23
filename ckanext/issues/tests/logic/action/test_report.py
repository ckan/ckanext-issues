from ckan import model
from ckan.lib import search
try:
    from ckan.tests import factories, helpers
except ImportError:
    from ckan.new_tests import factories, helpers

from ckanext.issues.tests import factories as issue_factories
from ckanext.issues.model import (
    Issue,
    IssueComment,
    IssueReport,
    IssueCommentReport
)
from ckanext.issues.exception import ReportAlreadyExists

from nose.tools import assert_equals, assert_raises
import mock


class TestReportAnIssue(object):
    def setup(self):
        pass

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_report_an_issue(self):
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
        helpers.call_action(
            'issue_report',
            context=context,
            dataset_id=dataset['id'],
            issue_number=issue['number']
        )

        issue_obj = Issue.get(issue['id'])
        assert_equals(len(issue_obj.abuse_reports), 1)
        assert_equals(issue_obj.spam_state, 'visible')

    def test_publisher_reports_an_issue(self):
        '''this should immediately hide the issue'''
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=owner, user_id=owner['id'],
                                      dataset_id=dataset['id'])

        context = {
            'user': owner['name'],
            'model': model,
        }
        helpers.call_action(
            'issue_report',
            context=context,
            dataset_id=dataset['id'],
            issue_number=issue['number']
        )

        result = helpers.call_action(
            'issue_show',
            dataset_id=dataset['id'],
            issue_number=issue['number'],
        )
        assert_equals('hidden', result['spam_state'])

    @mock.patch('ckanext.issues.logic.action.action.config')
    def test_max_strikes_hides_issues(self, mock):
        # mock out the config value of max_strikes
        mock.get.return_value = '1'
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])

        user_0 = factories.User()
        context = {
            'user': user_0['name'],
            'model': model,
        }
        helpers.call_action(
            'issue_report',
            context=context,
            dataset_id=dataset['id'],
            issue_number=issue['number']
        )

        user_1 = factories.User()
        context = {
            'user': user_1['name'],
            'model': model,
        }
        helpers.call_action(
            'issue_report',
            context=context,
            dataset_id=dataset['id'],
            issue_number=issue['number']
        )

        issue_obj = Issue.get(issue['id'])
        assert_equals(len(issue_obj.abuse_reports), 2)
        assert_equals('hidden', issue_obj.spam_state)


#class TestReportAnIssueTwice(object):
#    def setup(self):
#        model.Session.close_all()
#
#    def teardown(self):
#        helpers.reset_db()
#        search.clear()
#
#    def test_report_twice(self):
#        owner = factories.User()
#        org = factories.Organization(user=owner)
#        dataset = factories.Dataset(owner_org=org['name'])
#        issue = issue_factories.Issue(user_id=owner['id'],
#                                      dataset_id=dataset['id'])
#
#        user = factories.User(name='unauthed')
#        context = {
#            'user': user['name'],
#            'model': model,
#        }
#        model.Session.begin_nested()
#        helpers.call_action(
#            'issue_report',
#            context=context,
#            dataset_id=dataset['id'],
#            issue_number=issue['number']
#        )
#        assert_raises(
#            ReportAlreadyExists,
#            helpers.call_action,
#            'issue_report',
#            context=context,
#            dataset_id=dataset['id'],
#            issue_number=issue['number']
#        )


class TestIssueReportClear(object):
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_clear_as_publisher(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'],
                                      spam_state='hidden')
        context = {
            'user': owner['name'],
            'model': model,
        }
        helpers.call_action(
            'issue_report_clear',
            context=context,
            dataset_id=dataset['id'],
            issue_number=issue['number']
        )
        result = helpers.call_action(
            'issue_show',
            dataset_id=dataset['id'],
            issue_number=issue['number'],
        )
        assert_equals('visible', result['spam_state'])

        issue_obj = Issue.get(issue['id'])
        assert_equals(len(issue_obj.abuse_reports), 0)

    def test_clear_as_user(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'],
                                      spam_state='hidden')
        user = factories.User()
        model.Session.add(IssueReport(user['id'], issue['id']))
        model.Session.commit()
        context = {
            'user': user['name'],
            'model': model,
        }
        helpers.call_action(
            'issue_report_clear',
            context=context,
            dataset_id=dataset['id'],
            issue_number=issue['number']
        )
        result = helpers.call_action('issue_show',
                                     dataset_id=dataset['id'],
                                     issue_number=issue['number'])
        assert_equals('visible', result['spam_state'])

        issue_obj = Issue.get(issue['id'])
        assert_equals(len(issue_obj.abuse_reports), 0)


class TestIssueReportShow(object):
    @classmethod
    def setupClass(self):
        helpers.reset_db()
        search.clear()

    def setup(self):
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])

        context = {
            'user': self.owner['name'],
            'model': model,
        }
        helpers.call_action('issue_report',
                            context=context,
                            dataset_id=self.dataset['id'],
                            issue_number=self.issue['number'])

        self.user_0 = factories.User()
        context = {
            'user': self.user_0['name'],
            'model': model,
        }
        helpers.call_action('issue_report', context=context,
                            dataset_id=self.dataset['id'],
                            issue_number=self.issue['number'])

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_issue_report_show_for_publisher(self):
        context = {
            'user': self.owner['name'],
            'model': model,
        }
        result = helpers.call_action(
            'issue_report_show',
            context=context,
            dataset_id=self.dataset['id'],
            issue_number=self.issue['number'],
        )
        assert_equals(set([self.owner['id'], self.user_0['id']]), set(result))

    def test_issue_report_show_for_user(self):
        context = {
            'user': self.user_0['name'],
            'model': model,
        }
        result = helpers.call_action(
            'issue_report_show',
            context=context,
            dataset_id=self.dataset['id'],
            issue_number=self.issue['number'],
        )
        assert_equals([self.user_0['id']], result)

    def test_issue_report_show_for_other(self):
        context = {
            'user': factories.User()['name'],
            'model': model,
        }
        result = helpers.call_action(
            'issue_report_show',
            context=context,
            dataset_id=self.dataset['id'],
            issue_number=self.issue['number'],
        )
        assert_equals([], result)


class TestReportComment(object):
    def setup(self):
        helpers.reset_db()

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_report_comment(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])
        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               dataset_id=dataset['id'],
                                               issue_number=issue['number'])


        user = factories.User(name='unauthed')
        context = {
            'user': user['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_report',
                            context=context,
                            dataset_id=dataset['id'],
                            issue_number=issue['number'],
                            comment_id=comment['id'])

        comment_obj = IssueComment.get(comment['id'])
        assert_equals(len(comment_obj.abuse_reports), 1)
        assert_equals(comment_obj.spam_state, 'visible')

    def test_publisher_reports_a_comment(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user=owner, user_id=owner['id'],
                                      dataset_id=dataset['id'])

        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               dataset_id=dataset['id'],
                                               issue_number=issue['number'])

        context = {
            'user': owner['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_report', context=context,
                            dataset_id=dataset['id'],
                            issue_number=issue['number'],
                            comment_id=comment['id'])

        result = helpers.call_action('issue_show',
                                     issue_number=issue['number'],
                                     dataset_id=dataset['id'])
        assert_equals('hidden', result['comments'][0]['spam_state'])

    @mock.patch('ckanext.issues.logic.action.action.config')
    def test_max_strikes_hides_comment(self, mock):
        # mock out the config value of max_strikes
        mock.get.return_value = '0'

        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])
        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               dataset_id=dataset['id'],
                                               issue_number=issue['number'])

        user = factories.User(name='unauthed')
        context = {
            'user': user['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_report', context=context,
                            dataset_id=dataset['id'],
                            issue_number=issue['number'],
                            comment_id=comment['id'])
        result = helpers.call_action('issue_show',
                                     dataset_id=dataset['id'],
                                     issue_number=issue['number'])
        comment_obj = IssueComment.get(comment['id'])
        assert_equals(len(comment_obj.abuse_reports), 1)
        assert_equals('hidden', result['comments'][0]['spam_state'])


#class TestReportCommentTwice(object):
#    def setup(self):
#        helpers.reset_db()
#
#    def teardown(self):
#        helpers.reset_db()
#        search.clear()
#
#    def test_report_twice(self):
#        model.Session.begin_nested()
#        owner = factories.User()
#        org = factories.Organization(user=owner)
#        dataset = factories.Dataset(owner_org=org['name'])
#        issue = issue_factories.Issue(user_id=owner['id'],
#                                      dataset_id=dataset['id'])
#
#        comment = issue_factories.IssueComment(user_id=owner['id'],
#                                               dataset_id=dataset['id'],
#                                               issue_number=issue['number'])
#
#        user = factories.User(name='unauthed')
#        context = {
#            'user': user['name'],
#            'model': model,
#        }
#        helpers.call_action('issue_comment_report',
#                            context=context,
#                            dataset_id=dataset['id'],
#                            issue_number=issue['number'],
#                            comment_id=comment['id'])
#
#        assert_raises(
#            ReportAlreadyExists,
#            helpers.call_action,
#            'issue_comment_report',
#            context=context,
#            dataset_id=dataset['id'],
#            issue_number=issue['number'],
#            comment_id=comment['id'],
#        )


class TestCommentReportClearAsPublisher(object):
    @classmethod
    def setup_class(self):
        helpers.reset_db()

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_clear_as_publisher(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])
        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               dataset_id=dataset['id'],
                                               issue_number=issue['number'],
                                               spam_state='hidden')
        context = {
            'user': owner['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_report_clear', context=context,
                            dataset_id=dataset['id'],
                            issue_number=issue['number'],
                            comment_id=comment['id'])
        result = helpers.call_action('issue_show',
                                     issue_number=issue['number'],
                                     dataset_id=dataset['id'])
        assert_equals('visible', result['comments'][0]['spam_state'])
        comment_obj = IssueComment.get(comment['id'])
        assert_equals(len(comment_obj.abuse_reports), 0)


class TestCommentReportClearAsUser(object):
    @classmethod
    def setup_class(self):
        helpers.reset_db()
    # only allow one test here,
    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_clear_as_user(self):
        owner = factories.User()
        org = factories.Organization(user=owner)
        dataset = factories.Dataset(owner_org=org['name'])
        issue = issue_factories.Issue(user_id=owner['id'],
                                      dataset_id=dataset['id'])
        comment = issue_factories.IssueComment(user_id=owner['id'],
                                               dataset_id=dataset['id'],
                                               issue_number=issue['number'])

        user = factories.User()
        model.Session.add(IssueReport(user['id'],
                                      dataset_id=dataset['id'],
                                      issue_number=issue['number'],
                                      ))
        model.Session.commit()
        context = {
            'user': user['name'],
            'model': model,
        }
        helpers.call_action('issue_comment_report_clear', context=context,
                            dataset_id=dataset['id'],
                            issue_number=issue['number'],
                            comment_id=comment['id'])

        comment_obj = IssueComment.get(comment['id'])
        assert_equals(len(comment_obj.abuse_reports), 0)
        assert_equals('visible', comment_obj.spam_state)
