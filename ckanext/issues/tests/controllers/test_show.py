from ckan.lib import search
from ckan.plugins import toolkit
try:
    from ckan.tests import helpers
    from ckan.tests import factories
    from ckan.tests.helpers import assert_in
except ImportError:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories
    from ckan.new_tests.helpers import assert_in

from ckanext.issues.tests import factories as issue_factories


class TestIssuesShowController(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestIssuesShowController, cls).setup_class()
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

    def test_show_issue(self):
        app = self._get_test_app()
        env = {'REMOTE_USER': self.user['name'].encode('ascii')}

        response = app.get(
            url=toolkit.url_for('issues_show',
                                dataset_id=self.dataset['id'],
                                issue_number=self.issue['number']),
            extra_environ=env,
        )
        assert_in(self.issue['title'], response)
        assert_in(self.issue['description'], response)
