try:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories
except ImportError:
    from ckan.tests import helpers
    from ckan.tests import factories
from ckanext.issues.tests import factories as issue_factories


class TestIssueApi(helpers.FunctionalTestBase):
    def setup(self):
        user = factories.User()
        dataset = factories.Dataset()

        issue = issue_factories.Issue(user=user,
                                      user_id=user['id'],
                                      dataset_id=dataset['id'])
        issue_factories.IssueComment(
            user_id=user['id'],
            issue_number=issue['number'],
            dataset_id=issue['dataset_id'],
        )

    def test_search_api(self):
        self._test_app.get("/api/3/action/issue_search", extra_environ={})
