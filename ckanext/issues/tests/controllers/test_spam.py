from cStringIO import StringIO

import bs4

from ckan import model
from ckan.plugins import toolkit
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

from ckanext.issues.model import Issue, IssueComment, AbuseStatus
from ckanext.issues.tests import factories as issue_factories
from ckanext.issues.tests.helpers import ClearOnTearDownMixin

from lxml import etree
from nose.tools import assert_equals, assert_in, assert_not_in


class TestModeratedAbuseReport(helpers.FunctionalTestBase):
    def setup(self):
        super(TestModeratedAbuseReport, self).setup()
        self.owner = factories.User()
        self.reporter = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])

        # issue_abuse is moderated - i.e. definitely abuse/spam
        self.issue_abuse = issue_factories.Issue(
            user=self.owner,
            user_id=self.owner['id'],
            dataset_id=self.dataset['id'])
        issue_abuse = Issue.get(self.issue_abuse['id'])
        issue_abuse.visibility = 'hidden'
        issue_abuse.report_abuse(model.Session, self.reporter['id'])
        issue_abuse.abuse_status = AbuseStatus.abuse.value
        issue_abuse.save()
        self.user = factories.User()
        self.app = self._get_test_app()

    def test_abuse_label_appears_for_admin(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue_abuse['number']),
            extra_environ=env,
        )
        res_chunks = parse_issues_show(response)
        assert_in('Test Issue', res_chunks['issue_name'])
        assert_in('Hidden from normal users', res_chunks['issue_comment_label'])
        assert_in('Moderated: abuse', res_chunks['issue_comment_label'])
        assert_in('1 user reports this is spam/abus', res_chunks['issue_comment_label'])
        assert_in(self.reporter['name'], res_chunks['issue_comment_label'])

    def test_reported_as_abuse_appears_in_search_as_admin(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        res_chunks = parse_issues_dataset(response)
        assert_in('1 issue found', res_chunks['issues_found'])
        assert_in('Test Issue', res_chunks['issue_name'])
        assert_in('Spam/Abuse - hidden from normal users', res_chunks['issue_comment_label'])

    def test_reported_as_abuse_does_not_appear_in_search_to_user_who_reported_it(self):
        env = {'REMOTE_USER': self.reporter['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        res_chunks = parse_issues_dataset(response)
        assert_in('0 issues found', res_chunks['issues_found'])

    def test_reported_as_abuse_does_not_appear_as_non_admin(self):
        env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        res_chunks = parse_issues_dataset(response)
        assert_in('0 issues found', res_chunks['issues_found'])
        assert_not_in('Spam', res_chunks['issue_comment_label'])


class TestUnmoderatedAbuseReport(helpers.FunctionalTestBase):
    def setup(self):
        super(TestUnmoderatedAbuseReport, self).setup()
        self.owner = factories.User()
        self.reporter = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])

        # issue_reported is reported by a user but not moderated - i.e. may be
        # abuse/spam but it is still visible
        self.issue_reported = issue_factories.Issue(
            user=self.owner,
            user_id=self.owner['id'],
            dataset_id=self.dataset['id'])
        issue_reported = Issue.get(self.issue_reported['id'])
        issue_reported.visibility = 'visible'
        issue_reported.report_abuse(model.Session, self.reporter['id'])
        issue_reported.abuse_status = AbuseStatus.unmoderated.value
        issue_reported.save()

        self.user = factories.User()
        self.app = self._get_test_app()

    def test_abuse_label_appears_for_admin(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue_reported['number']),
            extra_environ=env,
        )
        res_chunks = parse_issues_show(response)
        assert_in('Test Issue', res_chunks['issue_name'])
        assert_not_in('Hidden from normal users', res_chunks['issue_comment_label'])
        assert_not_in('Moderated', res_chunks['issue_comment_label'])
        assert_in('1 user reports this is spam/abuse', res_chunks['issue_comment_label'])
        assert_in(self.reporter['name'], res_chunks['issue_comment_label'])

    def test_reported_as_abuse_appears_in_search_as_admin(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        res_chunks = parse_issues_dataset(response)
        assert_in('1 issue found', res_chunks['issues_found'])
        assert_in('Test Issue', res_chunks['issue_name'])
        assert_not_in('Spam/Abuse', res_chunks['issue_comment_label'])
        # Would be good if it said it had reports though

    def test_reported_as_abuse_appears_in_search_to_user_who_reported_it(self):
        env = {'REMOTE_USER': self.reporter['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        res_chunks = parse_issues_dataset(response)
        assert_in('1 issue found', res_chunks['issues_found'])
        assert_in('Test Issue', res_chunks['issue_name'])
        assert_in('Reported by you to admins', res_chunks['issue_comment_label'])

    def test_reported_as_abuse_appears_as_non_admin(self):
        env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        response = self.app.get(
            url=toolkit.url_for('issues_dataset',
                                dataset_id=self.dataset['id']),
            extra_environ=env,
        )
        res_chunks = parse_issues_dataset(response)
        assert_in('1 issue found', res_chunks['issues_found'])
        assert_in('Test Issue', res_chunks['issue_name'])
        assert_not_in('Spam', res_chunks['issue_comment_label'])


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


class TestReportIssue(helpers.FunctionalTestBase):
    def setup(self):
        super(TestReportIssue, self).setup()
        self.joe_public = factories.User()
        self.owner = factories.User()
        self.org = factories.Organization(user=self.owner)
        self.dataset = factories.Dataset(user=self.owner,
                                         owner_org=self.org['name'])
        self.issue = issue_factories.Issue(user=self.owner,
                                           user_id=self.owner['id'],
                                           dataset_id=self.dataset['id'])
        self.app = self._get_test_app()

    def test_report(self):
        env = {'REMOTE_USER': self.joe_public['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        response = response.follow()
        soup = bs4.BeautifulSoup(response.body)
        flash_messages = soup.find('div', {'class': 'flash-messages'}).text
        assert_in('Issue reported to an administrator', flash_messages)

    def test_report_as_admin(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        response = response.follow(extra_environ=env)
        soup = bs4.BeautifulSoup(response.body)
        flash_messages = soup.find('div', {'class': 'flash-messages'}).text
        assert_in('Report acknowledged. Marked as abuse/spam. '
                  'Issue is invisible to normal users.', flash_messages)

    def test_report_as_anonymous_user(self):
        response = self.app.post(
            url=toolkit.url_for('issues_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
        )
        response = response.follow()
        assert_in('You must be logged in to report issues',
                  response.body)

    def test_report_an_issue_that_does_not_exist(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_report',
                                dataset_id=self.dataset['id'],
                                issue_number='1235455'),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(response.status_int, 404)

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


class TestReportComment(helpers.FunctionalTestBase):
    def setup(self):
        super(TestReportComment, self).setup()
        self.joe_public = factories.User()
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

    def test_report(self):
        env = {'REMOTE_USER': self.joe_public['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_comment_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number'],
                                comment_id=self.comment['id']),
            extra_environ=env,
        )
        response = response.follow()
        soup = bs4.BeautifulSoup(response.body)
        flash_messages = soup.find('div', {'class': 'flash-messages'}).text
        assert_in('Comment has been reported to an administrator',
                  flash_messages)

    def test_report_as_admin(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_comment_report',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number'],
                                comment_id=self.comment['id']),
            extra_environ=env,
        )
        response = response.follow()
        soup = bs4.BeautifulSoup(response.body)
        flash_messages = soup.find('div', {'class': 'flash-messages'}).text
        assert_in('Report acknowledged. Marked as abuse/spam. '
                  'Comment is invisible to normal users.', flash_messages)

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

    def test_report_an_issue_that_does_not_exist(self):
        env = {'REMOTE_USER': self.owner['name'].encode('ascii')}
        response = self.app.post(
            url=toolkit.url_for('issues_comment_report',
                                dataset_id=self.dataset['id'],
                                issue_number='1235455',
                                comment_id=self.comment['id']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equals(response.status_int, 404)

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
        assert_in('Spam/abuse report cleared', response.body)

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
        assert_in('Spam/abuse report cleared', response.body)

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
