import logging
import os
import bottle

from .types import Property, PropertySet
from .web import FetchByQuery


ROOT = '/tmp'


class App:
    BASE = '/testcase'

    @classmethod
    def create(self):
        app = bottle.Bottle()
        
        app.route(
            path='/',
            callback=FetchByQuery(list_testcases, QueryClass=TestCaseQuery),
        )
        app.route(
            path='/<category>/<name>',
            callback=lambda category, name: get_testcase(category, name),
        )

        return app



class TestCase(PropertySet):
    name = Property()
    url = Property()


class TestCaseCategory(PropertySet):
    name = Property()
    entries = Property(TestCase, is_list=True)


class TestCaseFeed(PropertySet):
    entries = Property(TestCaseCategory, is_list=True)


class TestCaseQuery(PropertySet):
    category = Property()
    
    @classmethod
    def FromRequest(self):
        q = TestCaseQuery()
        q.category = bottle.request.query.category
        return q


def list_testcases(query=None):
    if query is not None:
        limit_to_category = query.category
    else:
        limit_to_category = None

    per_category = {}
    folder = FolderScanner(ROOT, 'md')
    for filepath in folder.scan():
        if os.path.sep not in filepath:
            continue
        category, filename = filepath.split(os.path.sep, 1)
        if os.path.sep in category:
            continue
        if limit_to_category and category != limit_to_category:
            continue
        testname = filename[:-3]
        if category in per_category.keys():
            per_category[category].append(testname)
        else:
            per_category[category] = [testname]

    return TestCaseFeed(
        entries=[
            TestCaseCategory(
                name=category,
                entries=[
                    TestCase(
                        name=testname,
                        url='%s/%s/%s' % (App.BASE, category, testname),
                    ) for testname in sorted(testnames)
                ],
            ) for category, testnames in sorted(per_category.items())
        ],
    )


def get_testcase(category, name):
    return bottle.static_file(os.path.join(category, name) + '.md', root=ROOT)


class FolderScanner(object):
    def __init__(self, basepath, ext=None):
        self.basepath = basepath
        self.ext = ext

    def scan(self):
        for r, ds, fs in os.walk(self.basepath):
            for f in fs:
                if not self.ext or f.split('.')[-1].lower() in self.ext:
                    p = os.path.relpath(os.path.join(r, f), self.basepath)
                    if not p.startswith('.'):
                        yield p

