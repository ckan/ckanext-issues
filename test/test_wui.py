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

class TestController(HtmlCheckMethods):

    @classmethod
    def setup_class(self):
        # Return a test app with the custom config.
        app = ckan.config.middleware.make_app(config['global_conf'], **config)
        self.app = webtest.TestApp(app)
        ckan.plugins.load('issues')
        ckan.tests.CreateTestData.create()
        self.sysadmin_user = ckan.model.User.get('testsysadmin')
        self.dataset = model.Package.get('annakarenina')
        self.extra_environ_tester = {'REMOTE_USER': 'tester'}

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('issues')
        model.repo.rebuild_db()

    def test_issue_new_get(self):
        # sysadmin = factories.Sysadmin()
        offset = url_for('new_issue', package_id=self.dataset.name)
        res = self.app.get(offset, status=200,
                extra_environ=self.extra_environ_tester)
        # res = self.strip_tags(unicode(res.body, 'utf8'))
        assert 'New Issue' in res.body, res.body

    def test_issue_new_post_bad_data(self):
        offset = url_for('new_issue', package_id=self.dataset.name)
        data = {
            'description': 'xxx'
            }
        res = self.app.post(offset,
                params=data,
                status=[200,302],
                extra_environ=self.extra_environ_tester
                )
        # no title ...
        assert 'The form contains invalid entries:' in res

    def test_issue_new_post(self):
        offset = url_for('new_issue', package_id=self.dataset.name)
        data = {
            'title': 'Test new issue',
            'description': 'xxx'
            }
        res = self.app.post(offset,
                params=data,
                status=[302],
                extra_environ=self.extra_environ_tester
                )

