'''Test the Issues Extension
'''
import paste.fixture
import pylons.test
import pylons.config as config
import webtest
from routes import url_for

import ckan.model as model
import ckan.logic as logic
import ckan.tests as tests
import ckan.plugins
import ckan.new_tests.factories as factories
from ckan.tests.html_check import HtmlCheckMethods

class TestLogic(object):
    @classmethod
    def setup_class(self):
        app = ckan.config.middleware.make_app(config['global_conf'], **config)
        self.app = webtest.TestApp(app)
        ckan.plugins.load('issues')
        ckan.tests.CreateTestData.create()
        self.sysadmin_user = ckan.model.User.get('testsysadmin')
        self.user = model.User.get('tester')
        self.dataset = model.Package.get('annakarenina')
        # test fixture
        context = {
            'model': model,
            'auth_user_obj': self.sysadmin_user,
            'user': self.sysadmin_user.name
        }
        # fixture issue
        self.issue = logic.get_action('issue_create')(context, {
            'title': 'General test issue',
            'description': 'Abc\n\n## Section',
            'dataset_id': self.dataset.id
        })
        self.issue2 = logic.get_action('issue_create')(context, {
            'title': 'General test issue 2',
            'description': '',
            'dataset_id': self.dataset.id
        })

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('issues')
        model.repo.rebuild_db()

    def test_create_requires_auth(self):
        out = tests.call_action_api(self.app, 'issue_create', status=403)

    def test_create_fails_if_no_dataset(self):
        issue = {
            'title': u'A data issue',
            'description': u'xxx',
            'dataset_id': 'made-up'
        }
        out = tests.call_action_api(self.app, 'issue_create',
                apikey=self.user.apikey, status=409,
                **issue
                )
        assert out['dataset_id'] == ['No dataset exists with id made-up'] , out

    def test_create_ok(self):
        issue = {
            'title': u'A data issue',
            'description': u'xxx',
            'dataset_id': self.dataset.name
        }
        out = tests.call_action_api(self.app, 'issue_create',
                apikey=self.user.apikey, status=200,
                **issue
                )
        assert out['title'] == issue['title'], out
        assert out['dataset_id'] == self.dataset.id, out
        assert out['status'] == 'open'
        assert len(out['comments']) == 0

    def test_show(self):
        new_issue_id = self.issue['id']
        out = tests.call_action_api(self.app, 'issue_show',
                apikey=self.user.apikey, status=200,
                id=new_issue_id
                )
        assert out['title'] == self.issue['title'], out
        assert len(out['comments']) == 0, out

    def test_create_comment(self):
        comment = {
            'comment': u'xxx',
            'issue_id': self.issue2['id']
        }
        out = tests.call_action_api(self.app, 'issue_comment_create',
                apikey=self.user.apikey,
                status=200,
                **comment
            )
        assert out['id'], out
        assert out['comment'] == comment['comment'], out

