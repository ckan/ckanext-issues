import mock

from nose.tools import assert_equals, assert_raises, assert_not_in, assert_in

try:
    from ckan.tests import factories, helpers
    from ckan.tests.helpers import FunctionalTestBase
except ImportError:
    from ckan.new_tests import factories, helpers
    from ckan.new_tests.helpers import FunctionalTestBase
from ckan.plugins import toolkit

from ckanext.issues.tests import factories as issue_factories
from ckanext.issues.model import Issue, IssueComment
from ckanext.issues.tests.helpers import ClearOnTearDownMixin
from ckanext.issues.logic.action.action import _get_recipients

from ckan import model


class TestIssueShow(ClearOnTearDownMixin):
    def setup(self):
        self.issue = issue_factories.Issue(title='Test Issue')

    def test_issue_show(self):
        issue = helpers.call_action(
            'issue_show',
            dataset_id=self.issue['dataset_id'],
            issue_number=self.issue['number'],
        )
        assert_equals('Test Issue', issue['title'])
        assert_equals('Some description', issue['description'])

    def test_issue_user_dictization(self):
        issue = helpers.call_action(
            'issue_show',
            dataset_id=self.issue['dataset_id'],
            issue_number=self.issue['number'],
        )
        user = issue['user']
        assert_equals('test.ckan.net', user['name'])
        assert_not_in('apikey', user.keys())
        assert_not_in('reset_key', user.keys())
        assert_not_in('password', user.keys())


class TestIssueNewWithEmailing(FunctionalTestBase, ClearOnTearDownMixin):
    def setup(self):
        self.user = factories.User()
        self.dataset = factories.Dataset()

    @classmethod
    def _apply_config_changes(cls, cfg):
        # Mock out the emailer
        from ckan.lib import mailer
        cls.mock_mailer = mock.MagicMock()
        mailer.mail_user = cls.mock_mailer
        cfg['ckanext.issues.send_email_notifications'] = True

    def test_issue_create(self):
        creator = factories.User(name='creator')
        admin = factories.User(name='admin')
        org = factories.Organization(
            users=[{'name': admin['id'], 'capacity': 'admin'}])
        dataset = factories.Dataset(owner_org=org['id'])

        # mock the render as it is easier to look at the variables passed in
        # than the rendered text
        with mock.patch('ckanext.issues.logic.action.action.render_jinja2') \
                as render_mock:
            issue_create_result = toolkit.get_action('issue_create')(
                context={'user': creator['name']},
                data_dict={
                    'title': 'Title',
                    'description': 'Description',
                    'dataset_id': dataset['id'],
                }
            )

        issue_object = Issue.get(issue_create_result['id'])
        assert_equals('Title', issue_object.title)
        assert_equals('Description', issue_object.description)
        assert_equals(1, issue_object.number)
        # some test user for the org called 'test.ckan.net' gets emailed too
        users_emailed = [call[1]['extra_vars']['recipient']['user_id']
                         for call in render_mock.call_args_list]
        assert_in(admin['id'], users_emailed)

    def test_issue_create_second(self):
        issue_0 = toolkit.get_action('issue_create')(
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': self.dataset['id'],
            }
        )
        issue_1 = toolkit.get_action('issue_create')(
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': self.dataset['id'],
            }
        )

        issue_object = Issue.get(issue_0['id'])
        assert_equals(1, issue_object.number)
        issue_object = Issue.get(issue_1['id'])
        assert_equals(2, issue_object.number)

    def test_issue_create_multiple_datasets(self):
        issue_0 = toolkit.get_action('issue_create')(
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': self.dataset['id'],
            }
        )
        issue_1 = toolkit.get_action('issue_create')(
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': self.dataset['id'],
            }
        )

        issue_object = Issue.get(issue_0['id'])
        assert_equals(1, issue_object.number)
        issue_object = Issue.get(issue_1['id'])
        assert_equals(2, issue_object.number)

        # create a second dataset
        dataset = factories.Dataset()
        issue_2 = toolkit.get_action('issue_create')(
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': dataset['id'],
            }
        )
        issue_object = Issue.get(issue_2['id'])
        # check that the issue number starts from 1
        assert_equals(1, issue_object.number)

    def test_issue_create_dataset_does_not_exist(self):
        issue_create = toolkit.get_action('issue_create')
        assert_raises(
            toolkit.ValidationError,
            issue_create,
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': 'nonsense',
            }
        )

    def test_issue_create_test_validation(self):
        issue_create = toolkit.get_action('issue_create')
        assert_raises(
            toolkit.ValidationError,
            issue_create,
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': 'not a datasest',
            }
        )

    def test_issue_create_cannot_set_abuse(self):
        issue_create_result = toolkit.get_action('issue_create')(
            context={'user': self.user['name']},
            data_dict={
                'title': 'Title',
                'description': 'Description',
                'dataset_id': self.dataset['id'],
                'visibility': 'hidden'
            }
        )
        issue_object = Issue.get(issue_create_result['id'])
        assert_equals('visible', issue_object.visibility)

    def test_get_recipients(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'])
        dataset_obj = model.Package.get(dataset['id'])

        recip = _get_recipients(context={}, dataset=dataset_obj)

        assert_equals(len(recip), 1)
        assert_equals(recip[0]['user_id'], user['id'])
        assert_equals(recip[0]['capacity'], 'Admin')
        assert_equals(recip[0]['organization_name'], org['name'])
        assert_equals(recip[0]['organization_title'], org['title'])


class TestIssueComment(FunctionalTestBase, ClearOnTearDownMixin):
    @classmethod
    def _apply_config_changes(cls, cfg):
        # Mock out the emailer
        from ckan.lib import mailer
        cls.mock_mailer = mock.MagicMock()
        mailer.mail_user = cls.mock_mailer
        cfg['ckanext.issues.send_email_notifications'] = True

    def test_create_comment_on_issue(self):
        creator = factories.User(name='creator')
        commenter = factories.User(name='commenter')
        admin = factories.User(name='admin')
        org = factories.Organization(
            users=[{'name': admin['id'], 'capacity': 'admin'}])
        dataset = factories.Dataset(owner_org=org['id'])

        issue = issue_factories.Issue(user=creator, user_id=creator['id'],
                                      dataset_id=dataset['id'])

        # mock the render as it is easier to look at the variables passed in
        # than the rendered text
        with mock.patch('ckanext.issues.logic.action.action.render_jinja2') \
                as render_mock:
            helpers.call_action(
                'issue_comment_create',
                context={'user': commenter['name']},
                issue_number=issue['number'],
                dataset_id=issue['dataset_id'],
                comment='some comment'
            )

        result = helpers.call_action(
            'issue_show',
            context={'user': commenter['name']},
            dataset_id=issue['dataset_id'],
            issue_number=issue['number']
        )
        comments = result['comments']
        assert_equals(len(comments), 1)
        assert_equals(comments[0]['comment'], 'some comment')
        assert_equals(comments[0]['user']['name'], 'commenter')
        # some test user for the org called 'test.ckan.net' gets emailed too
        users_emailed = [call[1]['extra_vars']['recipient']['user_id']
                         for call in render_mock.call_args_list]
        assert_in(admin['id'], users_emailed)

    def test_create_comment_on_closed_issue(self):
        user = factories.User()
        dataset = factories.Dataset()

        # create and close our issue
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        closed = helpers.call_action(
            'issue_update',
            issue_number=issue['number'],
            dataset_id=dataset['id'],
            context={'user': user['name']},
            status='closed'
        )
        assert_equals('closed', closed['status'])

        # check we can comment on closed issues
        helpers.call_action(
            'issue_comment_create',
            context={'user': user['name']},
            issue_number=issue['number'],
            dataset_id=dataset['id'],
            comment='some comment'
        )

        result = helpers.call_action(
            'issue_show',
            context={'user': user['name']},
            issue_number=issue['number'],
            dataset_id=dataset['id'],
        )

        comments = result['comments']
        assert_equals(len(comments), 1)
        assert_equals(comments[0]['comment'], 'some comment')

    def test_cannot_create_empty_comment(self):
        user = factories.User()
        dataset = factories.Dataset()

        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        assert_raises(
            toolkit.ValidationError,
            helpers.call_action,
            'issue_comment_create',
            context={'user': user['name']},
            issue_number=issue['number'],
            dataset_id=issue['dataset_id'],
        )


class TestIssueSearch(ClearOnTearDownMixin):
    def test_list_all_issues_for_dataset(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        search_res = helpers.call_action('issue_search',
                                         context={'user': user['name']},
                                         dataset_id=dataset['id'],
                                         sort='oldest')
        issues_list = search_res['results']
        assert_equals([i['id'] for i in created_issues],
                      [i['id'] for i in issues_list])
        assert_equals(search_res['count'], 10)

    def test_list_all_issues_for_organization(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'])

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          organization_id=org['id'],
                                          sort='oldest')['results']
        assert_equals([i['id'] for i in created_issues],
                      [i['id'] for i in issues_list])

    def test_list_all_issues(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          sort='oldest')['results']
        assert_equals([i['id'] for i in created_issues],
                      [i['id'] for i in issues_list])

    def test_limit(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        search_res = helpers.call_action(
            'issue_search',
            context={'user': user['name']},
            dataset_id=dataset['id'],
            sort='oldest',
            limit=5
        )
        issues_list = search_res['results']
        assert_equals([i['id'] for i in created_issues][:5],
                      [i['id'] for i in issues_list])
        assert_equals(search_res['count'], 10)

    def test_offset(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='oldest',
                                          offset=5)['results']
        assert_equals([i['id'] for i in created_issues][5:],
                      [i['id'] for i in issues_list])

    def test_pagination(self):
        user = factories.User()
        dataset = factories.Dataset()

        created_issues = [issue_factories.Issue(user=user, user_id=user['id'],
                                                dataset_id=dataset['id'],
                                                description=i)
                          for i in range(0, 10)]
        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='oldest',
                                          offset=5,
                                          limit=3)['results']
        assert_equals([i['id'] for i in created_issues][5:8],
                      [i['id'] for i in issues_list])

    def test_filter_newest(self):
        user = factories.User()
        dataset = factories.Dataset()

        issues = [issue_factories.Issue(
            user=user,
            user_id=user['id'],
            dataset_id=dataset['id'],
            description=i
        ) for i in range(0, 10)]

        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='newest')['results']
        assert_equals(list(reversed([i['id'] for i in issues])),
                      [i['id'] for i in issues_list])

    def test_filter_least_commented(self):
        user = factories.User()
        dataset = factories.Dataset()

        # issue#1 has 3 comment. #2 has 1 comments, etc
        comment_count = [3, 1, 2]
        issue_ids = []
        for i in comment_count:
            issue = issue_factories.Issue(user_id=user['id'],
                                          dataset_id=dataset['id'],
                                          description=i)
            issue_ids.append(issue['id'])

            for j in range(0, i):
                issue_factories.IssueComment(
                    user_id=user['id'],
                    issue_number=issue['number'],
                    dataset_id=issue['dataset_id'],
                )
        reordered_ids = [issue_ids[1], issue_ids[2], issue_ids[0]]

        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='least_commented')['results']
        assert_equals(reordered_ids, [i['id'] for i in issues_list])
        assert_equals([1, 2, 3], [i['comment_count'] for i in issues_list])

    def test_filter_most_commented(self):
        user = factories.User()
        dataset = factories.Dataset()

        # issue#1 has 3 comment. #2 has 1 comments, etc
        comment_count = [3, 1, 2, 0]
        issue_ids = []
        for i in comment_count:
            issue = issue_factories.Issue(user_id=user['id'],
                                          dataset_id=dataset['id'],
                                          description=i)
            issue_ids.append(issue['id'])

            for j in range(0, i):
                issue_factories.IssueComment(
                    user_id=user['id'],
                    issue_number=issue['number'],
                    dataset_id=issue['dataset_id'],
                )

        reordered_ids = [issue_ids[0], issue_ids[2], issue_ids[1],
                         issue_ids[3]]

        issues_list = helpers.call_action('issue_search',
                                          context={'user': user['name']},
                                          dataset_id=dataset['id'],
                                          sort='most_commented')['results']
        assert_equals(reordered_ids, [i['id'] for i in issues_list])
        assert_equals([3, 2, 1, 0], [i['comment_count'] for i in issues_list])

    def test_filter_by_title_string_search(self):
        user = factories.User()
        dataset = factories.Dataset()

        issues = [issue_factories.Issue(user_id=user['id'],
                                        dataset_id=dataset['id'],
                                        title=title)
                  for title in ['some title', 'another Title', 'issue']]

        filtered_issues = helpers.call_action('issue_search',
                                              context={'user': user['name']},
                                              dataset_id=dataset['id'],
                                              q='title')['results']

        expected_issue_ids = set([i['id'] for i in issues[:2]])
        assert_equals(expected_issue_ids,
                      set([i['id'] for i in filtered_issues]))


class TestIssueUpdate(ClearOnTearDownMixin):
    def test_update_an_issue(self):
        user = factories.User()
        dataset = factories.Dataset()
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        helpers.call_action(
            'issue_update',
            context={'user': user['name']},
            issue_number=issue['number'],
            dataset_id=dataset['id'],
            title='new title',
            description='new description'
        )

        updated = helpers.call_action(
            'issue_show',
            dataset_id=dataset['id'],
            issue_number=issue['number'],
        )
        assert_equals('new title', updated['title'])
        assert_equals('new description', updated['description'])

    def test_reopen_an_issue(self):
        '''This test is resolve a bug where updating/reopening an issue
        deletes it. Magical'''
        user = factories.User()
        dataset = factories.Dataset()
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        closed = helpers.call_action(
            'issue_update',
            context={'user': user['name']},
            dataset_id=dataset['id'],
            issue_number=issue['number'],
            status='closed'
        )
        assert_equals('closed', closed['status'])

        after_closed = helpers.call_action(
            'issue_show',
            context={'user': user['name']},
            dataset_id=dataset['id'],
            issue_number=issue['number'],
        )
        assert_equals('closed', after_closed['status'])

        helpers.call_action(
            'issue_update',
            context={'user': user['name']},
            dataset_id=dataset['id'],
            issue_number=issue['number'],
            status='open',
        )

        reopened = helpers.call_action(
            'issue_show',
            context={'user': user['name']},
            dataset_id=dataset['id'],
            issue_number=issue['number'],
        )
        assert_equals('open', reopened['status'])

    def test_cannot_update_visiblity_using_update(self):
        '''we don't want users to be able to set their own abuse status'''
        user = factories.User()
        dataset = factories.Dataset()
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])
        helpers.call_action(
            'issue_update',
            context={'user': user['name']},
            dataset_id=dataset['id'],
            issue_number=issue['number'],
            visibility='hidden'
        )

        after_update = helpers.call_action(
            'issue_show',
            context={'user': user['name']},
            issue_number=issue['number'],
            dataset_id=dataset['id'],
        )
        assert_equals('visible', after_update['visibility'])

    def test_updating_issue_that_does_not_exist_raises_not_found(self):
        user = factories.User()
        dataset = factories.Dataset()

        assert_raises(
            toolkit.ObjectNotFound,
            helpers.call_action,
            'issue_update',
            context={'user': user['name']},
            dataset_id=dataset['id'],
            issue_number=10000000,
        )

    def test_updating_issue_nonexisting_dataset_raises_not_found(self):
        user = factories.User()
        assert_raises(
            toolkit.ValidationError,
            helpers.call_action,
            'issue_update',
            context={'user': user['name']},
            dataset_id='does-not-exist',
            issue_number=10000000,
        )


class TestIssueDelete(ClearOnTearDownMixin):
    def test_deletion(self):
        user = factories.User()
        dataset = factories.Dataset()
        issue = issue_factories.Issue(user=user, user_id=user['id'],
                                      dataset_id=dataset['id'])

        helpers.call_action('issue_delete',
                            context={'user': user['name']},
                            dataset_id=dataset['id'],
                            issue_number=issue['number'])

        assert_raises(toolkit.ObjectNotFound,
                      helpers.call_action,
                      'issue_show',
                      dataset_id=dataset['id'],
                      issue_number=issue['number'])

    def test_delete_nonexistent_issue_raises_not_found(self):
        user = factories.User()
        dataset = factories.Dataset()
        assert_raises(toolkit.ObjectNotFound,
                      helpers.call_action,
                      'issue_delete',
                      context={'user': user['name']},
                      dataset_id=dataset['id'],
                      issue_number='2')

    def test_delete_non_integer_parameter_issue_raises_not_found(self):
        '''issue ids are a postgres seqeunce currently'''
        user = factories.User()
        dataset = factories.Dataset()
        assert_raises(toolkit.ValidationError,
                      helpers.call_action,
                      'issue_delete',
                      context={'user': user['name']},
                      dataset_id=dataset['id'],
                      issue_number='huh')


class TestOrganizationUsersAutocomplete(ClearOnTearDownMixin):
    def test_fetch_org_editors(self):
        owner = factories.User(name='test_owner')
        editor = factories.User(name='test_editor')
        admin = factories.User(name='test_admin')
        member = factories.User(name='test_member')
        factories.User(name='test_user')
        organization = factories.Organization(user=owner, users=[
            {'name': editor['id'], 'capacity': 'editor'},
            {'name': admin['id'], 'capacity': 'admin'},
            {'name': member['id']}, ])

        result = helpers.call_action('organization_users_autocomplete',
                                     q='test',
                                     organization_id=organization['id'])
        assert_equals(
            set(['test_owner', 'test_editor', 'test_admin']),
            set([i['name'] for i in result])
        )


class TestCommentSearch(ClearOnTearDownMixin):
    def setup(self):
        # Organization 1
        self.organization = factories.Organization()
        dataset = factories.Dataset(owner_org=self.organization['id'])
        issue = issue_factories.Issue(dataset_id=dataset['id'])

        self.comment1 = issue_factories.IssueComment(
            issue_number=issue['number'],
            dataset_id=issue['dataset_id'],
        )
        comment_object = IssueComment.get(self.comment1['id'])
        comment_object.change_visibility(model.Session, u'hidden')

        self.comment2 = issue_factories.IssueComment(  # unreported comment
            issue_number=issue['number'],
            dataset_id=issue['dataset_id'],
        )

        # Organization 2
        self.organization2 = factories.Organization()
        dataset2 = factories.Dataset(owner_org=self.organization2['id'])
        issue2 = issue_factories.Issue(dataset_id=dataset2['id'])

        self.comment3 = issue_factories.IssueComment(
            issue_number=issue2['number'],
            dataset_id=issue2['dataset_id'],
        )
        comment_object = IssueComment.get(self.comment3['id'])
        comment_object.change_visibility(model.Session, u'hidden')

        self.comment4 = issue_factories.IssueComment(  # unreported comment
            issue_number=issue2['number'],
            dataset_id=issue2['dataset_id'],
        )

    def test_reported_search_for_org(self):
        result = helpers.call_action('issue_comment_search',
                                     organization_id=self.organization['id'],
                                     only_hidden=True)

        assert_equals([self.comment1['id']],
                      [c['id'] for c in result.get('results')])

    def test_reported_search(self):
        result = helpers.call_action('issue_comment_search',
                                     only_hidden=True)

        assert_equals([self.comment1['id'], self.comment3['id']],
                      [c['id'] for c in result.get('results')])

    def test_search_for_org(self):
        result = helpers.call_action('issue_comment_search',
                                     organization_id=self.organization['id'])

        assert_equals([self.comment1['id'], self.comment2['id']],
                      [c['id'] for c in result.get('results')])

    def test_search(self):
        result = helpers.call_action('issue_comment_search')

        assert_equals([self.comment1['id'],
                       self.comment2['id'],
                       self.comment3['id'],
                       self.comment4['id']],
                      [c['id'] for c in result.get('results')])
