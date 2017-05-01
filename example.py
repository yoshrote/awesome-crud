"""
curl -XPOST -d"{}" http://localhost:8000/articles
curl -XGET -d"{}" http://localhost:8000/articles
curl -XOPTIONS -d"{}" http://localhost:8000/articles
curl -XGET -d"{}" http://localhost:8000/articles/100
curl -XDELETE -d"{}" http://localhost:8000/articles/100
curl -XPUT -d"{}" http://localhost:8000/articles/100
curl -XPATCH -d"{}" http://localhost:8000/articles/100

curl -XPOST -d"{}" http://localhost:8000/articles/_bulk
curl -XPUT -d"{}" http://localhost:8000/articles/_bulk
curl -XPATCH -d"{}" http://localhost:8000/articles/_bulk
curl -XDELETE -d"{}" http://localhost:8000/articles/_bulk
"""
import json
import logging
from wsgiref.simple_server import make_server

from awesome_crud import Application, BaseDAO, Node

LOG = logging.getLogger('example')

class FooDAO(BaseDAO):
    def __init__(self, request):
        self.request = request

    def create(self, body):
        LOG.info('create')
        return {'create': self.NAME}

    def query(self, body, order='asc', offset=0, limit=None):
        LOG.info('query')
        return [
            {'query': self.NAME},
            {'order': order},
            {'offset': offset},
            {'limit': limit}
        ]

    def update(self, body):
        LOG.info('update')
        return {'update': self.NAME}

    def patch(self, body):
        LOG.info('patch')
        return {'patch': self.NAME}

    def delete(self, body):
        LOG.info('delete')
        return {'delete': self.NAME}

    def get(self, body):
        LOG.info('get')
        return {'get': self.NAME}

    def bulk_create(self, body):
        LOG.info('bulk_create')
        return {'bulk_create': self.NAME}

    def bulk_update(self, body):
        LOG.info('bulk_update')
        return {'bulk_update': self.NAME}

    def bulk_patch(self, body):
        LOG.info('bulk_patch')
        return {'bulk_patch': self.NAME}

    def bulk_delete(self, body):
        LOG.info('bulk_delete')
        return {'bulk_delete': self.NAME}


class ArticleDAO(FooDAO):
    NAME = 'articles'


class AuthorDAO(FooDAO):
    NAME = 'authors'


class TagDAO(FooDAO):
    NAME = 'tags'


class ArticleNode(Node):
    CONTEXT = ArticleDAO


class AuthorNode(Node):
    CONTEXT = AuthorDAO


class TagNode(Node):
    CONTEXT = TagDAO


class SampleApplication(Application):
    RESOURCE_TREE = {
        'articles': ArticleNode({
            'authors': AuthorNode({}),
            'tags': TagNode({})
        }),
        'authors': AuthorNode({
            'articles': ArticleNode({}),
            'tags': TagNode({
                'articles': ArticleNode({})
            })
        }),
        'tags': TagNode({
            'articles': ArticleNode({})
        })
    }

    def __init__(self):
        app_config = {
            'serialization': {
                'mime': 'application/json',
                'serializer': json,
                'charset': 'utf-8',
                'empty': '{}',
            },
            'db': None,
        }
        super(SampleApplication, self).__init__(app_config)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    simple_app = SampleApplication()
    httpd = make_server('', 8000, simple_app)
    LOG.info("Serving on port 8000...")
    httpd.serve_forever()
