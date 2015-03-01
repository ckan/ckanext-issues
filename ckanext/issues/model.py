"""
CKAN Issue Extension Data Model
"""
from ckan import model
from ckan.model import meta, User, Package, Session, Resource
import ckan.lib.helpers as h

import ckan.model.domain_object as domain_object
from datetime import datetime
import logging

import enum
from sqlalchemy import func, types, Table, ForeignKey, Column
from sqlalchemy.orm import relation, backref, joinedload

log = logging.getLogger(__name__)

issue_table = None
issue_category_table = None
issue_comment_table = None


def setup():
    """
    Called at the end of CKAN setup.

    Create issue and issue_category tables in the database.
    Prepopulate issue_category table with default categories.
    """
    if issue_table is None:
        define_issue_tables()
        log.debug('Issue tables defined in memory')

    if model.package_table.exists():
        issue_category_table.create(checkfirst=True)
        issue_table.create(checkfirst=True)
        issue_comment_table.create(checkfirst=True)

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
        session.commit()
        log.debug('Issue tables created')
    else:
        log.debug('Issue Extension tables already exist')

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
    return out


class IssueFilter(enum.Enum):
    newest = 1
    oldest = 2


class Issue(domain_object.DomainObject):
    """A Issue Object"""
    pass

    @classmethod
    def get(cls, reference, session=Session):
        """Returns a Issue object referenced by its id."""
        return session.query(cls).filter(cls.id == reference).first()

    @classmethod
    def get_issues_for_dataset(cls, dataset_id, offset=None, limit=None,
                               status=None, sort=None, session=Session):
        query = session.query(cls).filter(cls.dataset_id == dataset_id)
        if status:
            query = query.filter(cls.status == status)

        if sort:
            if sort == IssueFilter.newest:
                query = query.order_by(cls.created.desc())
            elif sort == IssueFilter.oldest:
                query = query.order_by(cls.created.asc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        query = query.options(joinedload(cls.comments))
        return (i.as_dict() for i in query.all())

    @classmethod
    def get_count_for_dataset(cls, dataset_id, session):
        query = session.query(func.count(cls.id)).\
            filter(cls.dataset_id == dataset_id).one()[0]
        return query

    def as_dict(self, include_comments=True, include_user=True):
        out = super(Issue, self).as_dict()

        if include_comments:
            out['comments'] = [c.as_dict() for c in self.comments]
        if include_user:
            out['user'] = _user_dict(self.user)
        # some cases dataset not yet set ...
        if self.dataset:
            out['ckan_url'] = h.url_for('issues_show',
                                        package_id=self.dataset.name,
                                        id=self.id)
        return out


class IssueComment(domain_object.DomainObject):
    """A Issue Comment Object"""
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


def define_issue_tables():
    global issue_category_table
    global issue_table
    global issue_comment_table

    issue_category_table = Table(
        'issue_category',
        meta.metadata,
        Column('id', types.Integer, primary_key=True, autoincrement=True),
        Column('name', types.Unicode(ISSUE_CATEGORY_NAME_MAX_LENGTH),
               nullable=False, unique=True),
        Column('description', types.Unicode, nullable=False, unique=False),
        Column('created', types.DateTime, default=datetime.now,
               nullable=False))

    issue_table = Table(
        'issue',
        meta.metadata,
        Column('id', types.Integer, primary_key=True, autoincrement=True),
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
        Column('resolver_id', types.UnicodeText,
               ForeignKey('user.id', onupdate='CASCADE', ondelete='SET NULL')),
        Column('status', types.String(15), default=ISSUE_STATUS.open,
               nullable=False),
        Column('resolved', types.DateTime),
        Column('created', types.DateTime, default=datetime.now, nullable=False)
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
               nullable=False))

    meta.mapper(
        Issue,
        issue_table,
        properties={
            'user': relation(
                model.User,
                backref=backref('issues', cascade='all, delete-orphan'),
                primaryjoin=issue_table.c.user_id.__eq__(User.id)
            ),
            'resolver': relation(
                model.User,
                backref=backref('resolved_issues',
                                cascade='all, delete-orphan'),
                primaryjoin=issue_table.c.resolver_id.__eq__(User.id)
            ),
            'dataset': relation(
                model.Package,
                backref=backref('issues', cascade='all, delete-orphan'),
                primaryjoin=issue_table.c.dataset_id.__eq__(Package.id)
            ),
            'resource': relation(
                model.Resource,
                backref=backref('issues', cascade='all, delete-orphan'),
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
