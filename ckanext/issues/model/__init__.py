"""
CKAN Issue Extension Data Model
"""
from ckan import model
from ckan.model import meta, User, Package, Session, Resource
import ckan.lib.helpers as h

import ckan.model.domain_object as domain_object
from ckan.lib.dictization import model_dictize

from ckanext.issues.model.report import define_report_tables

from datetime import datetime
import logging

import enum
from sqlalchemy import func, types, Table, ForeignKey, Column, Index
from sqlalchemy.orm import relation, backref, subqueryload
from sqlalchemy.sql.expression import or_

log = logging.getLogger(__name__)

issue_table = None
issue_category_table = None
issue_comment_table = None
issue_report_table = None
issue_comment_report_table = None


def setup():
    """
    Called at the end of CKAN setup.

    Create issue and issue_category tables in the database.
    Prepopulate issue_category table with default categories.
    """
    if issue_table is None:
        define_issue_tables()
        report_tables = define_report_tables([Issue, IssueComment])
        log.debug('Issue tables defined in memory')

    if not model.package_table.exists():
        # during tests?
        return

    if not issue_table.exists():
        issue_category_table.create(checkfirst=True)
        issue_table.create(checkfirst=True)
        issue_comment_table.create(checkfirst=True)

        if report_tables:
            for table in report_tables:
                table.create(checkfirst=True)
        log.debug('Issue tables created')

        # add default categories if they don't already exist
        session = model.meta.Session()
        for category_name, category_desc in DEFAULT_CATEGORIES.iteritems():
            if not category_name:
                continue

            category = IssueCategory.get(category_name)
            if not category:
                category = IssueCategory(category_name)
                category.description = category_desc
                session.add(category)
        if session.new:
            log.debug('Issue categories created')
            session.commit()
    else:
        log.debug('Issue tables already exist')

ISSUE_CATEGORY_NAME_MAX_LENGTH = 100
DEFAULT_CATEGORIES = {u"broken-resource-link": "Broken data link",
                      u"no-author": "No publisher or author specified",
                      u"bad-format": "Data incorrectly formatted",
                      u"no-resources": "No resources in the dataset",
                      u"add-description": "No description of the data",
                      u"other": "Other"}

ISSUE_STATUS = domain_object.Enum('open', 'closed')


class IssueCategory(object):
    """A Issue Category Object"""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<IssueCategory('%s')>" % (self.name)

    @classmethod
    def get(cls, reference):
        """Returns a IssueCategory object referenced by its id or name."""
        if type(reference) is int:
            # if reference is an integer, get by ID
            return Session.query(cls).filter(cls.id == reference).first()
        else:
            # if not, get by name
            return Session.query(cls).filter(cls.name == reference).first()

    @classmethod
    def search(cls, querystr, sqlalchemy_query=None):
        """ Search IssueCategory names """
        if not sqlalchemy_query:
            query = model.Session.query(cls)
        else:
            query = sqlalchemy_query
        qstr = '%' + querystr + '%'
        return query.filter(cls.name.ilike(qstr))


# make a nice user dict object
def _user_dict(user):
    out = user.as_dict()
    out['ckan_url'] = h.url_for('user_datasets', id=user.name)
    out['gravatar'] = h.gravatar(user.email_hash, size=48)
    out['gravatar_url'] = '''//gravatar.com/avatar/%s?s=%d''' % (user.email_hash, 48)
    return out


class IssueFilter(enum.Enum):
    newest = 'Newest'
    oldest = 'Oldest'
    most_commented = 'Most Commented'
    least_commented = 'Least Commented'
    recently_updated = 'Recently Update'
    least_recently_updated = 'Least Recently Updated'

    @classmethod
    def get_filter(cls, issue_filter):
        '''Takes an IssueFilter, and returns a sqlalchemy filtering function

        The filtering function returned takes and sqlalchemy query and applies
        the filter to the sqlalchemy query'''
        sort_functions = {
            cls.newest: lambda q: q.order_by(Issue.created.desc()),
            cls.oldest: lambda q: q.order_by(Issue.created.asc()),
            cls.least_commented:
                lambda q: q.order_by(func.count(IssueComment.id).asc()),
            cls.most_commented:
                lambda q: q.order_by(func.count(IssueComment.id).desc()),
            cls.recently_updated:
                lambda q: q.order_by(func.max(IssueComment.created).asc()),
            cls.least_recently_updated:
                lambda q: q.order_by(func.max(IssueComment.created).desc()),
        }
        try:
            return sort_functions[issue_filter]
        except KeyError:
            raise InvalidIssueFilterException()


class InvalidIssueFilterException(object):
    pass


class Issue(domain_object.DomainObject):
    """A Issue Object"""

    @classmethod
    def get(cls, reference, session=Session):
        """Returns an Issue object referenced by its id."""
        return session.query(cls).filter(cls.id == reference).first()

    @classmethod
    def get_by_number(cls, dataset_id, issue_number, session=Session):
        return session.query(cls)\
            .filter(cls.dataset_id == dataset_id)\
            .filter(cls.number == issue_number)\
            .first()

    @classmethod
    def apply_filters_to_an_issue_query(
            cls, query,
            organization_id=None, dataset_id=None,
            status=None, q=None,
            spam_state=None,
            include_sub_organizations=False):
        if dataset_id:
            query = query.filter(cls.dataset_id == dataset_id)
        if organization_id:
            org = model.Group.get(organization_id)
            assert org
            query = query.join(model.Package,
                               cls.dataset_id == model.Package.id)
            if include_sub_organizations:
                orgs = (org_.id
                        for org_
                        in org.get_children_groups(type='organization'))
                query = query.filter(model.Package.owner_org.in_(orgs))
            else:
                query = query.filter(model.Package.owner_org == org.id)

        if q:
            search_expr = '%{0}%'.format(q)
            query = query.filter(or_(cls.title.ilike(search_expr),
                                     cls.description.ilike(search_expr)))

        if status:
            query = query.filter(cls.status == status)
        if spam_state:
            query = query.filter(cls.spam_state == spam_state)
        return query

    @classmethod
    def get_issues(cls, organization_id=None, dataset_id=None,
                   offset=None, limit=None,
                   status=None, sort=None, q=None,
                   spam_state=None, session=Session,
                   include_sub_organizations=False,
                   include_datasets=False,
                   include_reports=False):
        comment_count = func.count(IssueComment.id).label('comment_count')
        last_updated = func.max(IssueComment.created).label('updated')
        query = session.query(
            cls,
            model.User.name,
            comment_count,
            last_updated,
        )
        query = cls.apply_filters_to_an_issue_query(
            query,
            organization_id=organization_id, dataset_id=dataset_id,
            status=status, q=q,
            spam_state=spam_state,
            include_sub_organizations=include_sub_organizations)
        if sort:
            try:
                query = IssueFilter.get_filter(sort)(query)
            except InvalidIssueFilterException:
                pass

        query = query.join(User, Issue.user_id == User.id)\
            .outerjoin(IssueComment, Issue.id == IssueComment.issue_id)\
            .group_by(model.User.name, Issue.id)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        if include_reports:
            query = query.options(subqueryload('abuse_reports'))

        return query

    @classmethod
    def get_count_for_dataset(cls, dataset_id=None, organization_id=None,
                              status=None, sort=None, q=None,
                              spam_state=None, session=Session,
                              include_sub_organizations=False):
        query = session.query(func.count(cls.id))
        query = cls.apply_filters_to_an_issue_query(
            query,
            organization_id=organization_id, dataset_id=dataset_id,
            status=status, q=q,
            spam_state=spam_state,
            include_sub_organizations=include_sub_organizations)
        return query.one()[0]

    def report_abuse(self, session, user_id, **kwargs):
        self.abuse_reports.append(self.Report(user_id, self.id))
        session.add(self)
        session.flush()
        return self

    def change_visiblity(self, session, visibility):
        self.spam_state = visibility
        session.add(self)
        session.flush()
        return self

    def clear_abuse_report(self, session, user_id):
        report = self.Report.get_reports_for_user(
            session,
            user_id=user_id,
            parent_id=self.id,
        ).first()
        if report:
            session.delete(report)
            session.flush()
        return self

    def clear_all_abuse_reports(self, session):
        self.change_visiblity(session, u'visible')
        for r in self.abuse_reports:
            session.delete(r)
        session.flush()
        return self

    def as_dict(self):
        out = super(Issue, self).as_dict()

        out['user'] = _user_dict(self.user)
        # some cases dataset not yet set ...
        if self.dataset:
            out['ckan_url'] = h.url_for('issues_show',
                                        dataset_id=self.dataset.name,
                                        issue_number=self.number)
        return out

    def as_plain_dict(self, user, comment_count, updated,
                      include_dataset=False, include_reports=False):
        '''Used for listing issues against a dataset

        Similar to as_dict, but we're not including full comments or the full
        user dict

        returns an issue_dict with a comment_count and a user as a string.
        '''
        out = super(Issue, self).as_dict()
        out.update({
            'user': user,
            'comment_count': comment_count,
            'updated': updated,
        })
        if include_dataset:
            pkg = self.dataset
            context = {'model': model, 'session': model.Session}
            out['dataset'] = model_dictize.package_dictize(pkg, context)
        if include_reports:
            out['abuse_reports'] = [i.user_id for i in self.abuse_reports]
        return out


class IssueComment(domain_object.DomainObject):
    """A Issue Comment Object"""
    @classmethod
    def get(cls, reference, session=Session):
        """Returns a Issue comment object referenced by its id."""
        return session.query(cls).filter(cls.id == reference).first()

    @classmethod
    def get_comments(cls, issue):
        """ Gets all comments for a given issue """
        return model.Session.query(cls).\
            filter(cls.issue_id == issue.id).order_by("-created")

    @classmethod
    def get_comment_count(cls, issue):
        """ Gets count of comments for a given issue """
        return model.Session.query(cls).\
            filter(cls.issue_id == issue.id).count()

    def as_dict(self):
        out = super(IssueComment, self).as_dict()
        out['user'] = _user_dict(self.user)
        return out

    def report_abuse(self, session, user_id, **kwargs):
        self.abuse_reports.append(IssueComment.Report(user_id, self.id))
        session.add(self)
        session.flush()
        return self

    def change_visibility(self, session, visibility):
        self.spam_state = visibility
        session.add(self)
        session.flush()
        return self

    def clear_abuse_report(self, session, user_id):
        report = IssueComment.Report.get_reports_for_user(session, user_id,
                                                          self.id).first()
        if report:
            session.delete(report)
            session.flush()
        return self

    def clear_all_abuse_reports(self, session):
        self.change_visibility(session, u'visible')
        for r in self.abuse_reports:
            session.delete(r)
        session.flush()
        return self


def define_issue_tables():
    global issue_category_table
    global issue_table
    global issue_comment_table
    global issue_report_table
    global issue_comment_report_table

    issue_category_table = Table(
        'issue_category',
        meta.metadata,
        Column('id', types.Integer, primary_key=True, autoincrement=True),
        Column('name', types.Unicode(ISSUE_CATEGORY_NAME_MAX_LENGTH),
               nullable=False, unique=True),
        Column('description', types.Unicode, nullable=False, unique=False),
        Column('created', types.DateTime, default=datetime.now,
               nullable=False))

    # TODO get rid of these foreign key relations - not allowed for extensions
    issue_table = Table(
        'issue',
        meta.metadata,
        Column('id', types.Integer, primary_key=True, autoincrement=True),
        Column('number', types.Integer, nullable=False),
        Column('title', types.UnicodeText, nullable=False),
        Column('description', types.UnicodeText),
        Column('dataset_id', types.UnicodeText,
               ForeignKey('package.id', onupdate='CASCADE',
                          ondelete='CASCADE'),
               nullable=False),
        Column('resource_id', types.UnicodeText,
               ForeignKey('resource.id', onupdate='CASCADE',
                          ondelete='CASCADE')),
        Column('user_id', types.UnicodeText,
               ForeignKey('user.id', onupdate='CASCADE', ondelete='SET NULL'),
               nullable=False),
        Column('assignee_id', types.UnicodeText,
               ForeignKey('user.id', onupdate='CASCADE', ondelete='SET NULL')),
        Column('status', types.String(15), default=ISSUE_STATUS.open,
               nullable=False),
        Column('resolved', types.DateTime),
        Column('created', types.DateTime, default=datetime.now,
               nullable=False),
        Column('spam_state', types.Unicode, default=u'visible'),
        Index('idx_issue_number_dataset_id', 'dataset_id', 'number',
              unique=True),
    )

    issue_comment_table = Table(
        'issue_comment',
        meta.metadata,
        Column('id', types.Integer, primary_key=True, autoincrement=True),
        Column('comment', types.Unicode, nullable=False),
        Column('user_id', types.Unicode,
               ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False, index=True),
        Column('issue_id', types.Integer,
               ForeignKey('issue.id', onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False, index=True),
        Column('created', types.DateTime, default=datetime.now,
               nullable=False),
        Column('spam_state', types.Unicode, default=u'visible'),
    )

    meta.mapper(
        Issue,
        issue_table,
        properties={
            'user': relation(
                model.User,
                backref=backref('issues', cascade='all, delete-orphan'),
                primaryjoin=issue_table.c.user_id.__eq__(User.id)
            ),
            'assignee': relation(
                model.User,
                backref=backref('resolved_issues',
                                cascade='all'),
                primaryjoin=issue_table.c.assignee_id.__eq__(User.id)
            ),
            'dataset': relation(
                model.Package,
                backref=backref('issues', cascade='all, delete-orphan'),
                primaryjoin=issue_table.c.dataset_id.__eq__(Package.id)
            ),
            'resource': relation(
                model.Resource,
                backref=backref('issues', cascade='all'),
                primaryjoin=issue_table.c.resource_id.__eq__(Resource.id)
            ),
        }
    )

    meta.mapper(IssueCategory, issue_category_table)

    meta.mapper(
        IssueComment,
        issue_comment_table,
        properties={
            'user': relation(
                model.User,
                backref=backref('issue_comments',
                                cascade='all, delete-orphan'),
                primaryjoin=issue_comment_table.c.user_id.__eq__(User.id)
            ),
            'issue': relation(
                Issue,
                backref=backref('comments', cascade='all, delete-orphan'),
                primaryjoin=issue_comment_table.c.issue_id.__eq__(Issue.id)
            ),
        }
    )
