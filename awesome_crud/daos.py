from . import BaseDao

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
