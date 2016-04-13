from ckan import model
from ckan.plugins import toolkit
try:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories
except ImportError:
    from ckan.tests import helpers
    from ckan.tests import factories

from ckanext.issues.tasks import check_spam_issue, check_spam_comment

from ckanext.issues.model import Issue, IssueComment, AbuseStatus
from ckanext.issues.tests import factories as issue_factories
from ckanext.issues.tests.helpers import ClearOnTearDownMixin

from nose.tools import assert_equals, assert_in, assert_not_in, raises
from nose.plugins.skip import SkipTest


class TestSpamCheckTask(helpers.FunctionalTestBase):

    def setup(self):
        # Skip tests if we do not have an APIKey in config
        from pylons import config
        if not config.get('ckanext.issues.akismet.key', ''):
            raise SkipTest("No akismet apikey specified")

        super(TestSpamCheckTask, self).setup()
        self.spammer = factories.User(name='viagratest123' )
        self.non_spammer = factories.User(name='bobsmith')
        self.org = factories.Organization(user=self.non_spammer)
        self.dataset = factories.Dataset(user=self.non_spammer,
                                         owner_org=self.org['name'])

        # issue_abuse is moderated - i.e. definitely abuse/spam
        self.issue_abuse = issue_factories.Issue(
            user=self.spammer,
            user_id=self.spammer['id'],
            dataset_id=self.dataset['id'],
            description='SPAM $$$')
        self.issue_fine = issue_factories.Issue(
            user=self.non_spammer,
            user_id=self.non_spammer['id'],
            dataset_id=self.dataset['id'],
            description='A perfectly reasonable comment in the grand scheme of things')

        self.user = factories.User()
        self.app = self._get_test_app()

    @raises(toolkit.ObjectNotFound)
    def test_spam(self):
        check_spam_issue(self.issue_abuse['dataset_id'], self.issue_abuse['number'])
        toolkit.get_action('issue_show')({}, {
            'dataset_id': self.issue_abuse['dataset_id'],
            'issue_number': self.issue_abuse['number']
        })

    def test_not_spam(self):
        check_spam_issue(self.issue_fine['dataset_id'], self.issue_fine['number'])
        res = toolkit.get_action('issue_show')({}, {
            'dataset_id': self.issue_fine['dataset_id'],
            'issue_number': self.issue_fine['number']
        })
        assert res['abuse_status'] == 'unmoderated'

