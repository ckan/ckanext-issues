from ckan.lib import search
from ckan.plugins import toolkit
try:
    from ckan.tests import helpers
    from ckan.tests import factories
except ImportError:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories
from ckan.tests.helpers import assert_in

from ckanext.issues.tests import factories as issue_factories
from ckanext.issues import model


class TestModeration(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestModeration, cls).setup_class()
        helpers.reset_db()
        search.clear()

    def setup(self):
        self.user = factories.User()
        self.organization = factories.Organization(user=self.user)

        self.dataset = factories.Dataset(user=self.user,
                                         owner_org=self.organization['name'],
                                         private=True)

        self.issue = issue_factories.Issue(user=self.user,
                                           user_id=self.user['id'],
                                           dataset_id=self.dataset['id'])

    def test_moderate_all_organization_issues(self):
        app = self._get_test_app()
        env = {'REMOTE_USER': self.user['name'].encode('ascii')}

        issue = model.Issue.get(self.issue['id'])
        issue.visibility = 'hidden'
        issue.save()

        response = app.get(
            url=toolkit.url_for('issues_moderate_reported_issues',
                                organization_id=self.organization['id']),
            extra_environ=env,
        )
        assert_in(self.issue['title'], response)
        assert_in(self.issue['description'], response)


class TestCommentModeration(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestCommentModeration, cls).setup_class()
        helpers.reset_db()
        search.clear()

    def setup(self):
        self.user = factories.User()
        self.organization = factories.Organization(user=self.user)

        self.dataset = factories.Dataset(user=self.user,
                                         owner_org=self.organization['name'])

        self.issue = issue_factories.Issue(user=self.user,
                                           user_id=self.user['id'],
                                           dataset_id=self.dataset['id'])
        self.comment = issue_factories.IssueComment(
            dataset_id=self.dataset['id'],
            issue_number=self.issue['number'],
            comment='this is a comment',
        )

    def test_moderate_all_organization_issues(self):
        app = self._get_test_app()
        env = {'REMOTE_USER': self.user['name'].encode('ascii')}

        comment = model.IssueComment.get(self.comment['id'])
        comment.visibility = 'hidden'
        comment.save()

        response = app.get(
            url=toolkit.url_for('issues_moderate_reported_comments',
                                organization_id=self.organization['id']),
            extra_environ=env,
        )
        assert_in(self.comment['comment'], response)
