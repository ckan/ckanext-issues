"""
CKAN Issue Extension Data Model
"""
import sqlalchemy as sa
from sqlalchemy import types, Table, ForeignKey, Column, DateTime
from sqlalchemy.sql.expression import or_
from sqlalchemy.orm import relation, backref
from ckan import model
from ckan.model import meta, User, Package, Session, Resource, Group
from ckan.model.types import make_uuid
from datetime import datetime

ISSUE_CATEGORY_NAME_MAX_LENGTH = 100
DEFAULT_CATEGORIES = {u"broken-resource-link": "Broken resource link",
                      u"no-author": "No author specified",
                      u"bad-format": "Data is in incorrect format",
                      u"no-resources": "There are no resources in the dataset",
                      u"add-description": "There is no description of the data",
                      u"other": "Other"}

# ------------------------------------------------------------------------------

issue_category_table = Table('issue_category', meta.metadata,
    Column('id', types.Integer, primary_key = True,
                autoincrement = True),
    Column('name', types.Unicode(ISSUE_CATEGORY_NAME_MAX_LENGTH),
                nullable=False, unique=True),
    Column('description', types.Unicode, nullable=False, unique=False),
    Column('created', types.DateTime, default = datetime.now, nullable = False))

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

# ------------------------------------------------------------------------------

issue_table = Table('issue', meta.metadata,
    Column('id', types.Integer, primary_key = True,
                autoincrement = True),
    Column('issue_category_id', types.Integer,
                ForeignKey('issue_category.id', onupdate = 'CASCADE', ondelete = 'CASCADE'),
                nullable = False),
    Column('package_id', types.UnicodeText,
                ForeignKey('package.id', onupdate = 'CASCADE', ondelete = 'CASCADE'),
                nullable = True),
    Column('resource_id', types.UnicodeText,
                ForeignKey('resource.id', onupdate = 'CASCADE', ondelete = 'CASCADE'),
                nullable = True),
    Column('description', types.UnicodeText, nullable = False),
    Column('creator', types.UnicodeText,
                ForeignKey('user.id', onupdate='CASCADE', ondelete='SET NULL'),
                nullable = False),
    Column('resolver', types.UnicodeText,
                ForeignKey('user.id', onupdate='CASCADE', ondelete='SET NULL'),
                nullable = True),
    Column('resolved', types.DateTime),
    Column('created', types.DateTime, default = datetime.now, nullable = False))

class Issue(object):
    """A Issue Object"""
    def __init__(self, category_id, description, creator):
        self.issue_category_id = category_id
        self.description = description
        self.creator = creator

    def __repr__(self):
        return "<Issue('%s')>" % (self.id)

    @classmethod
    def get(cls, reference):
        """Returns a Issue object referenced by its id."""
        return Session.query(cls).filter(cls.id == reference).first()

meta.mapper(Issue, issue_table, properties={
    'category': relation(IssueCategory,
        backref=backref('issues_all', cascade='all, delete-orphan')
    ),
    'reporter': relation(model.User,
        backref=backref('raised_issues', cascade='all, delete-orphan'),
        primaryjoin=issue_table.c.creator.__eq__(User.id)
    ),
    'resolving_user': relation(model.User,
        backref=backref('resolved_issues', cascade='all, delete-orphan'),
        primaryjoin=issue_table.c.resolver.__eq__(User.id)
    ),
    'package': relation(model.Package,
        backref=backref('raised_issues', cascade='all, delete-orphan'),
        primaryjoin=issue_table.c.package_id.__eq__(Package.id)
    ),
    'resource': relation(model.Resource,
        backref=backref('raised_issues', cascade='all, delete-orphan'),
        primaryjoin=issue_table.c.resource_id.__eq__(Resource.id)
    ),})


meta.mapper(IssueCategory, issue_category_table)

# ------------------------------------------------------------------------------

issue_comment_table = Table('issue_comment', meta.metadata,
    Column('id', types.Integer, primary_key = True,
                autoincrement = True),
    Column('comment', types.Unicode, nullable=False, unique=False),
    Column('author_id', types.Unicode,
                ForeignKey('user.id', onupdate = 'CASCADE', ondelete = 'CASCADE'),
                nullable=False, unique=False),
    Column('issue_id', types.Integer,
                ForeignKey('issue.id', onupdate = 'CASCADE', ondelete = 'CASCADE'),
                nullable=False, unique=False, index=True),
    Column('created', types.DateTime, default = datetime.now, nullable = False))

class IssueComment(object):
    """A Issue Comment Object"""
    def __repr__(self):
        return "<IssueComment('%s')>" % (self.comment)

    @classmethod
    def get_comments(cls, issue):
        """ Gets all comments for a given issue """
        return model.Session.query(cls).\
            filter(cls.issue_id==issue.id).order_by("-created")

    @classmethod
    def get_comment_count(cls, issue):
        """ Gets count of comments for a given issue """
        return model.Session.query(cls).\
            filter(cls.issue_id==issue.id).count()

meta.mapper(IssueComment, issue_comment_table, properties={
    'author': relation(model.User,
        backref=backref('issue_comments', cascade='all, delete-orphan'),
        primaryjoin=issue_comment_table.c.author_id.__eq__(User.id)
    ),
    'issue': relation(Issue,
        backref=backref('comments', cascade='all, delete-orphan'),
        primaryjoin=issue_comment_table.c.issue_id.__eq__(Issue.id)
    ),})
