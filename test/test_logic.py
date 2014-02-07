'''Test the Issues Extension
'''
import paste.fixture
import pylons.test
import pylons.config as config
import webtest
from routes import url_for

import ckan.model as model
import ckan.tests as tests
import ckan.plugins
import ckan.new_tests.factories as factories
from ckan.tests.html_check import HtmlCheckMethods

class TestController(object):
    @classmethod
    def setup_class(self):
        app = ckan.config.middleware.make_app(config['global_conf'], **config)
        self.app = webtest.TestApp(app)
        ckan.plugins.load('issues')
        ckan.tests.CreateTestData.create()
        self.sysadmin_user = ckan.model.User.get('testsysadmin')
        self.user = model.User.get('tester')
        self.dataset = model.Package.get('annakarenina')

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('issues')
        model.repo.rebuild_db()

    def _test_create_requires_auth(self):
        out = tests.call_action_api(self.app, 'issue_create', status=403)

    def test_create_ok(self):
        issue = {
            'title': u'A data issue',
            'description': u'xxx',
            'dataset': self.dataset.name
        }
        out = tests.call_action_api(self.app, 'issue_create',
                apikey=self.user.apikey, status=200,
                **issue
                )
        assert out['title'] == issue['title'], out
        assert out['dataset_id'] == self.dataset.id, out

        new_issue_id = out['id']
        
        # test get for this issue
        out = tests.call_action_api(self.app, 'issue_show',
                apikey=self.user.apikey, status=200,
                id=new_issue_id
                )
        assert out['title'] == issue['title'], out

