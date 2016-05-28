import logging
import bottle
import datetime

from sqlalchemy import Column, DateTime, String, Integer, func
from samtt import get_db, Base
from enum import IntEnum

from .web import (
    Fetch,
    FetchByQuery,
)
from .types import Property, PropertySet
from .token import authenticate_cookie, get_me
from .testcase import list_testcases, App as TestcaseApp


class State(IntEnum):
    not_run = 0
    passed = 1
    failed = 2
    blocked = 3
    skipped = 4
    assigned = 5


class _Record(Base):
    __tablename__ = 'record'
    
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime(timezone=True), default=func.now())
    test_category = Column(String(128), nullable=False)
    test_name = Column(String(128), nullable=False)
    assignee = Column(String(128), nullable=True)
    run = Column(String(128), nullable=False)
    state = Column(Integer, nullable=False, default=State.not_run)
    comment = Column(String(4096))
    jira = Column(String(128))


class Record(PropertySet):
    id = Property(int)
    ts = Property()
    test_category = Property()
    test_name = Property()
    assignee = Property()
    run = Property()
    state = Property(enum=State, default=State.not_run)
    comment = Property()
    jira = Property()
    url = Property()
    history_url = Property()

    @classmethod
    def map_in(self, record):
        return Record(
            id=record.id,
            ts=record.ts.strftime('%Y-%m-%d %H:%M:%S'),
            test_category=record.test_category,
            test_name=record.test_name,
            assignee=record.assignee,
            run=record.run,
            state=record.state,
            comment=record.comment,
            jira=record.jira,
            url='%s/%s/%s' % (TestcaseApp.BASE, record.test_category, record.test_name),
            history_url='%s/history/%s/%s' % (App.BASE, record.test_category, record.test_name),
        )

    def map_out(self, record):
        record.ts = (datetime.datetime.strptime(
            self.ts, '%Y-%m-%d %H:%M:%S').replace(microsecond=0)
            if self.ts else None
        )
        record.test_category = self.test_category
        record.test_name = self.test_name
        record.assignee = self.assignee
        record.run = int(self.run)
        record.state = self.state
        record.comment = self.comment
        record.jira = self.jira


class RecordHistory(PropertySet):
    name = Property()
    entries = Property(Record, is_list=True)
    current = Property(Record)


class RecordCategoryWithHistory(PropertySet):
    name = Property()
    entries = Property(RecordHistory, is_list=True)


class RecordCategory(PropertySet):
    name = Property()
    entries = Property(Record, is_list=True)


class RecordFeed(PropertySet):
    history = Property(bool, default=False)
    count = Property(int)
    total_count = Property(int)
    entries = Property(RecordCategory, is_list=True)


class RecordFeedWithHistory(PropertySet):
    history = Property(bool, default=False)
    count = Property(int)
    total_count = Property(int)
    entries = Property(RecordCategoryWithHistory, is_list=True)


class App:
    BASE = '/record'

    @classmethod
    def create(self):
        app = bottle.Bottle()
        app.add_hook('before_request', authenticate_cookie)

        app.route(
            path='/',
            callback=Fetch(get_records),
        )

        app.route(
            path='/sync',
            method='POST',
            callback=sync_records,
        )

        app.route(
            path='/op/<category>/<test>/<state>',
            method='PUT',
            callback=op_record,
        )

        app.route(
            path='/history/<category>/<test>',
            callback=get_record_summary_for_test_case,
        )

        return app


def get_records(history=False, only_category=None, only_test_case=None):
    run = bottle.request.token.run
    with get_db().transaction() as t:
        q = t.query(_Record).filter(_Record.run == run)

        if only_category is not None:
            q = q.filter(_Record.test_category == only_category)

        if only_test_case is not None:
            q = q.filter(_Record.test_name == only_test_case)

        q = q.order_by(
            _Record.test_category.desc(),
            _Record.test_name.desc(),
            _Record.ts.asc(),
        )

        records = q.all()

        per_category = {}
        count = 0
        for _record in records:
            record = Record.map_in(_record)
            if record.test_category not in per_category.keys():
                per_category[record.test_category] = {}

            if history:
                if record.test_name not in per_category[record.test_category].keys():
                    per_category[record.test_category][record.test_name] = []
                    count += 1

                per_category[record.test_category][record.test_name].append(record)
            else:
                if record.test_name not in per_category[record.test_category]:
                    count += 1
                per_category[record.test_category][record.test_name] = record

    if history:
        return RecordFeedWithHistory(
            history=True,
            count=count,
            entries=[
                RecordCategoryWithHistory(
                    name=category,
                    entries=[
                        RecordHistory(
                            name=name,
                            entries=records,
                            current=records[-1],
                        ) for name, records in sorted(per_name.items())
                    ]
                ) for category, per_name in sorted(per_category.items())
            ]
        )
    else:
        for category, records in sorted(per_category.items()):
            print(category)
            print(records)
        return RecordFeed(
            history=False,
            count=count,
            entries=[
                RecordCategory(
                    name=category,
                    entries=[record for name, record in sorted(records.items())],
                ) for category, records in sorted(per_category.items())
            ]
        )


def get_record_summary_for_test_case(category, test):
    records = get_records(history=True, only_category=category, only_test_case=test)
    print(records.to_json())
    history = records.entries[0].entries[0]
    return history.to_dict()


def sync_records():
    run = bottle.request.token.run
    test_cases = list_testcases()
    for category in test_cases.entries:
        for test_case in category.entries:
            with get_db().transaction() as t:
                q = (
                    t.query(_Record)
                        .filter(
                            _Record.run == run,
                            _Record.test_category == category.name,
                            _Record.test_name == test_case.name
                    )
                )
                if q.count() == 0:
                    logging.debug('Creating record for %s/%s/%s' % (run, category.name, test_case.name))
                    r = _Record(
                        run=run,
                        test_category=category.name,
                        test_name=test_case.name,
                        state=int(State.not_run),
                    )
                    t.add(r)


def op_record(category, test, state):
    if category == 'undefined' or test == 'undefined':
        raise bottle.HTTPError(400)

    run = bottle.request.token.run
    assignee = bottle.request.token.name
    state = getattr(State, state)
    
    if bottle.request.json is not None:
        comment = bottle.request.json.get('comment', None) or None
        jira = bottle.request.json.get('jira', None) or None
    else:
        comment = None
        jira = None

    with get_db().transaction() as t:
        r = _Record(
            run=run,
            assignee=assignee,
            test_category=category,
            test_name=test,
            state=int(state),
            comment=comment,
            jira=jira,
        )
        t.add(r)

    return Record(
        run=run,
        assignee=assignee,
        test_name=test,
        test_category=category,
        state=state,
        comment=comment,
        jira=jira,
        url='%s/%s/%s' % (TestcaseApp.BASE, category, test),
        history_url='%s/history/%s/%s' % (App.BASE, category, test),
    ).to_dict()
