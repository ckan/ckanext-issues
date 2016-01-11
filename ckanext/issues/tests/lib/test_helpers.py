from ckanext.issues.tests.helpers import ClearOnTearDownMixin
from ckanext.issues.tests import factories as issue_factories
from ckanext.issues.model import Issue, IssueComment, AbuseStatus
from ckanext.issues.lib.util import issue_count, issue_comments, issue_comment_count
try:
    from ckan.tests import factories, helpers
except ImportError:
    from ckan.new_tests import factories, helpers

from nose.tools import assert_equals, assert_raises, assert_not_in


class TestUtils(ClearOnTearDownMixin):
    def setup(self):
        # Organization 1
        self.organization = factories.Organization()
        self.dataset = factories.Dataset(owner_org=self.organization['id'])
        self.issue = issue_factories.Issue(dataset_id=self.dataset['id'])

        self.comment1 = issue_factories.IssueComment(
            issue_number=self.issue['number'],
            dataset_id=self.issue['dataset_id'],
        )

        self.comment2 = issue_factories.IssueComment(
            issue_number=self.issue['number'],
            dataset_id=self.issue['dataset_id'],
        )

        self.comment3 = issue_factories.IssueComment(
            issue_number=self.issue['number'],
            dataset_id=self.issue['dataset_id'],
        )

        # Organization 2
        self.organization2 = factories.Organization()
        dataset2 = factories.Dataset(owner_org=self.organization2['id'])
        issue2 = issue_factories.Issue(dataset_id=dataset2['id'])

        self.comment4 = issue_factories.IssueComment(
            issue_number=issue2['number'],
            dataset_id=issue2['dataset_id'],
        )

        self.comment5 = issue_factories.IssueComment(  # unreported comment
            issue_number=issue2['number'],
            dataset_id=issue2['dataset_id'],
        )

    def test_issue_count(self):
        assert_equals(issue_count(self.dataset), 1)

    def test_issue_comment_count(self):
        assert_equals(issue_comment_count(self.issue), 3)

    def test_issue_comments(self):
        comments = issue_comments(self.issue)
        assert_equals([self.comment1['id'], self.comment2['id'], self.comment3['id']],
                      [comment.id for comment in comments])
