"""
curl -XPOST -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles
curl -XGET -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles
curl -XOPTIONS -H "Accept: application/json" -H "Content-type: application/json" -i -d"{}" http://localhost:8000/articles

curl -XGET -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles/100
curl -XDELETE -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles/100
curl -XPUT -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles/100
curl -XPATCH -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles/100

curl -XPOST -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles/_bulk
curl -XPUT -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles/_bulk
curl -XPATCH -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles/_bulk
curl -XDELETE -H "Accept: application/json" -H "Content-type: application/json" -d"{}" http://localhost:8000/articles/_bulk
"""
import json
import logging
from wsgiref.simple_server import make_server

from awesome_crud import Application, Node
from awesome_crud.daos import EchoDao

LOG = logging.getLogger('example')


def make_node(name, base_dao=EchoDao, base_node=Node):
    class NewDAO(base_dao):
        NAME = name

    class NewNode(base_node):
        CONTEXT = NewDAO

    return NewNode


ArticleNode = make_node('articles', base_dao=EchoDao)
AuthorNode = make_node('authors', base_dao=EchoDao)
TagNode = make_node('tags', base_dao=EchoDao)


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
                'application/json': {
                    'serializer': json,
                    'charset': 'utf-8',
                    'empty': '{}',
                }
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
