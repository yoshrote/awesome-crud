import logging

from webob.exc import HTTPNotImplemented

LOG = logging.getLogger(__name__)


class BaseDAO(object):
    # routing and parameter key
    NAME = None

    def __init__(self, registry):
        self.registry = registry

    @classmethod
    def get_pk(cls, resource):
        raise NotImplementedError('get_pk')

    def create(self, url_params, body):
        raise HTTPNotImplemented()

    def query(self, url_params, query_params):
        raise HTTPNotImplemented()

    def get(self, url_params):
        raise HTTPNotImplemented()

    def delete(self, url_params):
        raise HTTPNotImplemented()

    def update(self, url_params, body):
        raise HTTPNotImplemented()

    def patch(self, url_params, body):
        raise HTTPNotImplemented()

    def bulk_create(self, url_params, body):
        raise HTTPNotImplemented()

    def bulk_update(self, url_params, body):
        raise HTTPNotImplemented()

    def bulk_patch(self, url_params, body):
        raise HTTPNotImplemented()

    def bulk_delete(self, url_params, body):
        raise HTTPNotImplemented()


class EchoDao(BaseDAO):
    def __init__(self, registry):
        self.registry = registry

    @classmethod
    def get_pk(cls, resource):
        return resource.get('id', '<unknown>')

    def create(self, url_params, body):
        LOG.info('create')
        return {'create': self.NAME}

    def query(self, url_params, query_params):
        LOG.info('query')
        return [
            {'query': self.NAME},
            {'order': query_params.get('order') or 'asc'},
            {'offset': int(query_params.get('offset') or 0)},
            {'limit': query_params.get('limit') or None}
        ]

    def update(self, url_params, body):
        LOG.info('update')
        return {'update': self.NAME}

    def patch(self, url_params, body):
        LOG.info('patch')
        return {'patch': self.NAME}

    def delete(self, url_params):
        LOG.info('delete')
        return {'delete': self.NAME}

    def get(self, url_params):
        LOG.info('get')
        return {'get': self.NAME}

    def bulk_create(self, url_params, body):
        LOG.info('bulk_create')
        return {'bulk_create': self.NAME}

    def bulk_update(self, url_params, body):
        LOG.info('bulk_update')
        return {'bulk_update': self.NAME}

    def bulk_patch(self, url_params, body):
        LOG.info('bulk_patch')
        return {'bulk_patch': self.NAME}

    def bulk_delete(self, url_params, body):
        LOG.info('bulk_delete')
        return {'bulk_delete': self.NAME}


class MemoryDao(BaseDAO):
    DB = {}

    @property
    def db(self):
        return self.__class__.DB

    def create(self, url_params, body):
        id_ = url_params[self.NAME]
        self.db[id_] = body

    def update(self, url_params, body):
        id_ = url_params[self.NAME]
        self.db[id_] = body

    def patch(self, url_params, body):
        id_ = url_params[self.NAME]
        self.db[id_].update(body)

    def delete(self, url_params):
        id_ = url_params[self.NAME]
        del self.db[id_]

    def get(self, url_params):
        id_ = url_params[self.NAME]
        return self.db[id_]

    def bulk_create(self, url_params, body):
        for doc in body:
            self.create(doc)

    def bulk_update(self, url_params, body):
        for doc in body:
            self.update(doc['id'], doc)

    def bulk_patch(self, url_params, body):
        for doc in body:
            self.patch(doc['id'], doc)

    def bulk_delete(self, url_params, body):
        for doc in body:
            self.delete(doc['id'])


class RedisDao(BaseDAO):
    def __init__(self, request, **connection_kwargs):
        import redis
        super(RedisDao, self).__init__(request)
        self.connection = redis.StrictRedis(**connection_kwargs)

    def create(self, url_params, body, pipeline=None):
        pipe = pipeline or self.connection
        pipe.set(body['id'], body)

    def update(self, url_params, body, pipeline=None):
        id_ = url_params[self.NAME]
        pipe = pipeline or self.connection
        pipe.set(id_, body)

    def patch(self, url_params, body, pipeline=None):
        id_ = url_params[self.NAME]
        current = self.get(id_)
        current.update(body)
        self.update(id_, body)

    def delete(self, url_params, pipeline=None):
        id_ = url_params[self.NAME]
        pipe = pipeline or self.connection
        pipe.delete(id_)

    def get(self, url_params, pipeline=None):
        id_ = url_params[self.NAME]
        pipe = pipeline or self.connection
        pipe.get(id_)

    def bulk_create(self, url_params, body):
        pipe = self.connection.pipeline()
        for doc in body:
            self.create(doc, pipeline=pipe)
        pipe.execute()

    def bulk_update(self, url_params, body):
        pipe = self.connection.pipeline()
        for doc in body:
            self.update(doc['id'], doc, pipeline=pipe)
        pipe.execute()

    def bulk_patch(self, url_params, body):
        pipe = self.connection.pipeline()
        for doc in body:
            self.patch(doc['id'], doc, pipeline=pipe)
        pipe.execute()

    def bulk_delete(self, url_params, body):
        pipe = self.connection.pipeline()
        for doc in body:
            self.delete(doc['id'], pipeline=pipe)
        pipe.execute()
