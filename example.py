import logging
from wsgiref.simple_server import make_server

from awesome_crud import Application, BaseDAO, ControllerFactory

LOG = logging.getLogger(__name__)

class FooDAO(BaseDAO):
    NAME = None

    def __init__(self, request):
        self.request = request

    def create(self, body):
        return {'created': self.NAME}

    def query(self, order='asc', offset=0, limit=None):
        return [
            {'query': self.NAME},
            {'order': order},
            {'offset': offset},
            {'limit': limit}
        ]

    def update(self, id_, body):
        return {'update': self.NAME}

    def patch(self, id_, body):
        return {'patch': self.NAME}

    def delete(self, id_):
        return {'delete': self.NAME}

    def get(self, id_):
        return {'get': self.NAME}

    def bulk_create(self, body):
        return {'bulk_create': self.NAME}

    def bulk_update(self, body):
        return {'bulk_update': self.NAME}

    def bulk_patch(self, body):
        return {'bulk_patch': self.NAME}

    def bulk_delete(self, body):
        return {'bulk_delete': self.NAME}


class ArticleDAO(FooDAO):
    NAME = 'article'


class AuthorDAO(FooDAO):
    NAME = 'author'


class TagDAO(FooDAO):
    NAME = 'tag'


class ArticleControllerFactory(ControllerFactory):
    NAME = 'articles'
    CONTEXT = ArticleDAO


class AuthorControllerFactory(ControllerFactory):
    NAME = 'authors'
    CONTEXT = AuthorDAO


class TagControllerFactory(ControllerFactory):
    NAME = 'tags'
    CONTEXT = TagDAO


class SampleApplication(Application):
    RESOURCE_TREE = {
        'articles': ArticleControllerFactory({
            'authors': AuthorControllerFactory({}),
            'tags': TagControllerFactory({})
        }),
        'authors': AuthorControllerFactory({
            'articles': ArticleControllerFactory({}),
            'tags': TagControllerFactory({
                'articles': ArticleControllerFactory({})
            })
        }),
        'tags': TagControllerFactory({
            'articles': ArticleControllerFactory({})
        })
    }

    def __init__(self):
        app_config = {
            'serialization': {
                'mime': 'application/json',
                'serializer': json,
                'charset': 'utf-8'
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
