from . import BaseDao

class EchoDao(BaseDao):
    def __init__(self, registry):
        self.registry = registry

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


class MemoryDao(BaseDao):
    DB = {}

    @property
    def db(self):
        return self.__class__.DB
    
    def create(self, body):
        self.db[body['id']] = body

    def query(self, body, order='asc', offset=0, limit=None):
        raise HTTPNotImplemented()

    def update(self, id_, body):
        self.db[id_] = body

    def patch(self, id_, body):
        self.db[id_].update(body)

    def delete(self, id_):
        del self.db[id_]

    def get(self, id_):
        return self.db[id_]

    def bulk_create(self, body):
        for doc in body:
            self.create(doc)

    def bulk_update(self, body):
        for doc in body:
            self.update(doc['id'], doc)

    def bulk_patch(self, body):
        for doc in body:
            self.patch(doc['id'], doc)

    def bulk_delete(self, body):
        for doc in body:
            self.delete(doc['id'])


class RedisDao(BaseDao):
    def __init__(self, request, **connection_kwargs):
        import redis
        super(RedisDao, self).__init__(request)
        self.connection = redis.StrictRedis(**connection_kwargs)

    def create(self, body, pipeline=None):
        pipe = pipeline or self.connection
        pipe.set(body['id'], body)

    def query(self, body, order='asc', offset=0, limit=None):
        raise HTTPNotImplemented()

    def update(self, id_, body, pipeline=None):
        pipe = pipeline or self.connection
        pipe.set(id_, body)

    def patch(self, id_, body, pipeline=None):
        current = self.get(_id)
        current.update(body)
        self.update(id_, body)

    def delete(self, id_, pipeline=None):
        pipe = pipeline or self.connection
        pipe.delete(id_)

    def get(self, id_, pipeline=None):
        pipe = pipeline or self.connection
        pipe.get(id_)

    def bulk_create(self, body):
        pipe = self.connection.pipeline()
        for doc in body:
            self.create(doc, pipeline=pipe)
        pipe.execute()

    def bulk_update(self, body):
        pipe = self.connection.pipeline()
        for doc in body:
            self.update(doc['id'], doc, pipeline=pipe)
        pipe.execute()

    def bulk_patch(self, body):
        pipe = self.connection.pipeline()
        for doc in body:
            self.patch(doc['id'], doc, pipeline=pipe)
        pipe.execute()

    def bulk_delete(self, body):
        pipe = self.connection.pipeline()
        for doc in body:
            self.delete(doc['id'], pipeline=pipe)
        pipe.execute()
