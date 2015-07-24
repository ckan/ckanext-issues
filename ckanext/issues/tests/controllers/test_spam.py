from cStringIO import StringIO

from ckan import model
from ckan.lib import search
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.model import Issue, IssueComment
from ckanext.issues.tests import factories as issue_factories

from lxml import etree
from nose.tools import assert_equals, assert_in


class TestAbuseReport(helpers.FunctionalTestBase):
    def setup(self):
        super(TestAbuseReport, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])
        issue = Issue.get(self.issue['id'])
        issue.visibility = 'hidden'
        issue.save()
        self.user = factories.User()
        self.app = self._get_test_app()

    def test_abuse_label_appears_for_publisher(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        res_chunks = parse_issues_show(response)
        assert_in('Test Issue', res_chunks['issue_name'])
        assert_in('Abuse', res_chunks['issue_comment_label'])

    def test_reported_as_abuse_appears_in_search_for_publisher(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        res_chunks = parse_issues_dataset(response)
        assert_in('1 issue found', res_chunks['issues_found'])
        assert_in('Test Issue', res_chunks['issue_name'])

    def test_reported_as_abuse_does_not_appear_for_user(self):
        env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        res_chunks = parse_issues_dataset(response)
        assert_in('0 issues found', res_chunks['issues_found'])


def pprint_html(trees):
    return '\n'.join([etree.tostring(tree, pretty_print=True).strip()
                      for tree in trees])


def primary_div(tree):
    # This xpath looks for 'primary' as a whole word
    return tree.xpath(
        "//div[contains(concat(' ', normalize-space(@class), ' '), ' primary ')]")[0]


def parse_issues_dataset(response):
    '''Given the response from a GET url_for issues_dataset,
    returns named chunks of it that can be tested.
    '''
    tree = etree.parse(StringIO(response.body), parser=etree.HTMLParser())
    primary_tree = primary_div(tree)
    return {
        'primary_tree': pprint_html(primary_tree),
        'issue_comment_label': pprint_html(primary_tree.xpath('//div[@class="issue-comment-label"]')),
        'issue_name': pprint_html(primary_tree.xpath('//h4[@class="list-group-item-name"]')),
        'issues_found': pprint_html(primary_tree.xpath('//h2[@id="issues-found"]')),
        }


def parse_issues_show(response):
    '''Given the response from a GET url_for issues_show,
    returns named chunks of it that can be tested.
    '''
    tree = etree.parse(StringIO(response.body), parser=etree.HTMLParser())
    primary_tree = primary_div(tree)
    return {
        'primary_tree': pprint_html(primary_tree),
        'issue_comment_label': pprint_html(primary_tree.xpath('//div[@class="issue-comment-label"]')),
        'issue_comment_action': pprint_html(primary_tree.xpath('//div[@class="issue-comment-action"]')),
        'issue_name': pprint_html(primary_tree.xpath('//h1[@class="page-heading"]')),
        }


class TestReport(helpers.FunctionalTestBase):
    def setup(self):
        super(TestReport, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])
        self.app = self._get_test_app()

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_report(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        response = response.follow()
        assert_in('Issue reported to an administrator', response.body)

    def test_report_as_anonymous_user(self):
        response = self.app.post(
            url=toolkit.url_for('issues_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
        )
        response = response.follow()
        assert_in('You must be logged in to report issues',
                  response.body)

    #def test_report_an_issue_that_does_not_exist(self):
    #    env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
    #    response = self.app.post(
    #        url=toolkit.url_for('issues_report',
    #                            dataset_id=self.dataset['id'],
    #                            issue_id='1235455'),
    #        extra_environ=env,
    #        expect_errors=True
    #    )
    #    assert_equals(response.status_int, 404)

    def test_report_clear(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_report_clear',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        response = response.follow()
        assert_in('Issue report cleared', response.body)

    def test_report_clear_normal_user(self):
        user = factories.User()
        model.Session.add(Issue.Report(user['id'],
                                      self.issue['id']))
        model.Session.commit()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_report_clear',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
            expect_errors=True
        )
        response = response.follow()
        assert_in('Issue report cleared', response.body)

    def test_reset_on_issue_that_does_not_exist(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_report_clear',
                                dataset_id=self.dataset['id'],
                                issue_number='1235455'),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(response.status_int, 404)


class TestCommentAbuseReports(helpers.FunctionalTestBase):
    def setup(self):
        super(TestCommentAbuseReports, self).setup()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])
        self.comment = issue_factories.IssueComment(
            user_id=self.owner['id'],
            dataset_id=self.dataset['id'],
            issue_number=self.issue['number']
        )
        self.app = self._get_test_app()

    def teardown(self):
        helpers.reset_db()
        search.clear()

    def test_report(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_comment_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number'],
                                comment_id=self.comment['id']),
            extra_environ=env,
        )
        response = response.follow()
        assert_in('Comment has been reported to an administrator',
                  response.body)

    def test_report_not_logged_in(self):
        response = self.app.post(
            url=toolkit.url_for('issues_comment_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number'],
                                comment_id=self.comment['id']),
        )
        response = response.follow()
        assert_in('You must be logged in to report comments',
                  response.body)

    #def test_report_an_issue_that_does_not_exist(self):
    #    env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
    #    response = self.app.post(
    #        url=toolkit.url_for('issues_comment_report',
    #                            dataset_id=self.dataset['id'],
    #                            issue_id='1235455',
    #                            comment_id=self.comment['id']),
    #        extra_environ=env,
    #        expect_errors=True
    #    )
    #    assert_equals(response.status_int, 404)

    def test_report_clear(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_comment_report_clear',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number'],
                                comment_id=self.comment['id']),
            extra_environ=env,
        )
        response = response.follow()
        assert_in('Abuse report cleared', response.body)

    def test_report_clear_state_normal_user(self):
        user = factories.User()
        model.Session.add(IssueComment.Report(user['id'], self.comment['id']))
        model.Session.commit()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_comment_report_clear',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number'],
                                comment_id=self.comment['id']),
            extra_environ=env,
        )
        response = response.follow()
        assert_in('Abuse report cleared', response.body)

    def test_reset_on_issue_that_does_not_exist(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_comment_report_clear',
                                dataset_id=self.dataset['id'],
                                issue_number='1235455',
                                comment_id='12312323'),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(response.status_int, 404)
