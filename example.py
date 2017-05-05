"""
curl -XPOST -d"{}" http://localhost:8000/articles
curl -XGET -d"{}" http://localhost:8000/articles
curl -XOPTIONS -i -d"{}" http://localhost:8000/articles
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

from awesome_crud import Application, Node
from awesome_crud.daos import EchoDao

LOG = logging.getLogger('example')

class ArticleDAO(EchoDao):
    NAME = 'articles'


class AuthorDAO(EchoDao):
    NAME = 'authors'


class TagDAO(EchoDao):
    NAME = 'tags'


class ArticleNode(Node):
    CONTEXT = ArticleDAO


class AuthorNode(Node):
    CONTEXT = AuthorDAO


class TagNode(Node):
    CONTEXT = TagDAO


class SampleApplication(Application):
    # tree nav
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
    # flat nav
    RESOURCE_MAP = {
        'authors': AuthorNode({}),
        'articles': ArticleNode({}),
        'tags': TagNode({}),
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
            'navigation': {
                'method': 'flat',
                'config': self.RESOURCE_MAP
            }
        }
        super(SampleApplication, self).__init__(app_config)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    simple_app = SampleApplication()
    httpd = make_server('', 8000, simple_app)
    LOG.info("Serving on port 8000...")
    httpd.serve_forever()
