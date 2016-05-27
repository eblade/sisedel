import logging
import bottle
import random
import string

from sqlalchemy import Column, String
from sqlalchemy.orm.exc import NoResultFound
from samtt import Base, get_db

from .types import PropertySet, Property
from .web import (
    FetchByKey,
    FetchById,
)


BASE_URI = '?'


class _Token(Base):
    __tablename__ = 'token'

    token = Column(String(32), primary_key=True)
    name = Column(String(128), nullable=False)
    run = Column(String(128), nullable=False)


class Token(PropertySet):
    token = Property()
    name = Property()
    run = Property()
    link = Property()

    @classmethod
    def map_in(self, token):
        return Token(
            token=token.token,
            name=token.name,
            run=token.run,
            link='%s%s/auth/%s' % (BASE_URI, App.BASE, token.token)
        )


class App:
    BASE = '/token'

    @classmethod
    def create(self):
        app = bottle.Bottle()
        
        app.route(
            path='/auth/<token_string>',
            callback=authenticate_and_redirect,
        )

        app.route(
            path='/me',
            callback=get_me,
        )

        app.route(
            path='/names/<token_string>',
            callback=get_names_by_run,
        )

        return app


def authenticate_and_redirect(token_string):
    authenticate(token_string)
    return bottle.redirect('/')


def get_me():
    authenticate_cookie()
    return bottle.request.token.to_dict()


def get_names_by_run(run):
    authenticate_cookie()
    with get_db().transaction() as t:
        tokens = t.query(_Token).filter(_Token.run == run).all()

        return {
            '*schema': 'Names',
            'entries': [token.name for token in tokens],
            'count': len(tokens),
        }


def authenticate_cookie(*args, **kwargs):
    token_string = bottle.request.get_cookie('token')
    if token_string is None:
        raise bottle.HTTPError(401)
    authenticate(token_string)


def authenticate(token_string):
    if hasattr(bottle.request, 'token'):
        token = bottle.request.token
        logging.debug("Already authenticated as %s (running as %s).", token.name, token.run)
        return
        
    with get_db().transaction() as t:
        token = t.query(_Token).get(token_string)

        if token is None:
            raise bottle.HTTPError(401)

        bottle.request.token = Token.map_in(token)
        bottle.response.set_cookie('token', token_string, path='/')

        logging.debug("Authenticated as %s (running as %s).", token.name, token.run)


def create_token(name, run):
    with get_db().transaction() as t:
        _token = _Token(
            name=name,
            run=run,
            token=''.join(random.SystemRandom().choice(
                string.ascii_lowercase + string.ascii_uppercase + string.digits
            ) for _ in range(32))
        )

        t.add(_token)
        token = Token.map_in(_token)
    logging.debug("Adding token for %s (running as %s).", token.name, token.run)
    return token
