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
        self.context = {
            'model': model,
            'auth_user_obj': self.sysadmin_user,
            'user': self.sysadmin_user.name
        }
        self.issue = logic.get_action('issue_create')(self.context, {
            'title': 'General test issue',
            'description': 'Abc\n\n## Section',
            'dataset_id': self.dataset.id
        })
        self.comment = logic.get_action('issue_comment_create')(self.context, {
            'issue_id': self.issue['id'],
            'comment': 'Test comment'
            })

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('issues')
        model.repo.rebuild_db()

    def test_issue_new_get(self):
        offset = url_for('issues_new', package_id=self.dataset.name)
        res = self.app.get(offset, status=200,
                extra_environ=self.extra_environ_tester)
        assert 'New Issue' in res.body, res.body

    def test_issue_new_post_bad_data(self):
        offset = url_for('issues_new', package_id=self.dataset.name)
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
        offset = url_for('issues_new', package_id=self.dataset.name)
        data = {
            'title': 'Test new issue',
            'description': 'xxx'
            }
        res = self.app.post(offset,
                params=data,
                status=[302],
                extra_environ=self.extra_environ_tester
                )

    def test_issue_show(self):
        offset = url_for('issues_show', package_id=self.dataset.name,
                id=self.issue['id'])
        res = self.app.get(offset, status=200)
        assert self.issue['title'] in res, res.body
        # part of the markdown-ized version of the description
        assert '<h2>Section</h2>' in res, res.body
        assert self.comment['comment'] in res, res.body
        assert 'Login to comment' in res, res.body

    def test_issue_comment_new_post(self):
        ourissue = logic.get_action('issue_create')(self.context, {
            'title': 'General test issue',
            'description': 'Abc\n\n## Section',
            'dataset_id': self.dataset.id
        })
        offset = url_for('issues_comments', package_id=self.dataset.name,
                id=ourissue['id'])
        data = {
            'comment': ''
            }
        res = self.app.post(offset,
                params=data,
                status=[302],
                extra_environ=self.extra_environ_tester
                )
        issueUpdate = logic.get_action('issue_show')(self.context, {
            'id': ourissue['id']
        })
        # update should have failed so no comment
        assert len(issueUpdate['comments']) == 0, issueUpdate

        data['comment'] = 'A valid comment'
        res = self.app.post(offset,
                params=data,
                status=[302],
                extra_environ=self.extra_environ_tester
                )
        issueUpdate = logic.get_action('issue_show')(self.context, {
            'id': ourissue['id']
        })
        assert len(issueUpdate['comments']) == 1, issueUpdate

        # lastly we will update with change in status as well
        # note user MUST be editor on dataset
        data['comment'] = 'A valid comment'
        data['close'] = ''
        res = self.app.post(offset,
                params=data,
                status=[302],
                extra_environ=self.extra_environ_tester
                )
        issueUpdate = logic.get_action('issue_show')(self.context, {
            'id': ourissue['id']
        })
        assert issueUpdate['status'] == 'closed'

