"""
Create:         POST    /
Get:            GET     /<id>
Update:         PUT     /<id>
Partial Update: PATCH   /<id>
Delete:         DELETE  /<id>
Bulk Create:    POST    /_bulk
    Body: [<obj1>, <obj2>, ..., <objN>]
Bulk Update:    PUT     /_bulk
    Body: [<obj1>, <obj2>, ..., <objN>]
Bulk Patch:     PATCH   /_bulk
    Body: [<obj1>, <obj2>, ..., <objN>]
Bulk Delete:    DELETE  /_bulk
    Body: [<id1>, <id2>, ..., <idN>]
Query:          GET     /
    Params:     default     options
        order:  asc         desc|asc
        offset: 0
        limit:  None
"""
from __future__ import unicode_literals
import json
import logging

from collections import OrderedDict

from webob import Request, Response
from webob.dec import wsgify
from webob.exc import (
    HTTPBadRequest,
    HTTPException,
    HTTPNotFound,
    HTTPMethodNotAllowed,
    HTTPNotImplemented,
)

LOG = logging.getLogger(__name__)

class BaseController(object):
    def __init__(self, context):
        self.dispatch = {
            'OPTIONS': self.options
        }
        self.context = context

    def __call__(self, request, parameters):
        try:
            func = self.dispatch[request.method]
        except KeyError:
            raise HTTPMethodNotAllowed()
        else:
            return func(request, parameters)

    def options(self, request, parameters):
        resp = Response()
        resp.allow = sorted(self.dispatch.keys())
        return resp

    @staticmethod
    def serialize_body(request):
        try:
            return request.serializer.loads(request.body)
        except ValueError:
            raise HTTPBadRequest(detail='could not serialize body')


class ResourceController(BaseController):
    def __init__(self, context):
        super(ResourceController, self).__init__(context)
        self.dispatch.update({
            'GET': self.query,
            'POST': self.create,
        })

    def create(self, request, parameters):
        return self.context(request).create(
            request,
            parameters,
            self.serialize_body(request)
        )

    def query(self, request, parameters):
        return self.context(request).query(
            request,
            parameters,
            order=request.GET.get('order', 'asc'),
            offset=int(request.GET.get('offset') or 0),
            limit=(
                int(request.GET.get('limit'))
                if request.GET.get('limit')
                else None))


class InstanceController(BaseController):
    def __init__(self, context):
        super(InstanceController, self).__init__(context)
        self.dispatch.update({
            'DELETE': self.delete,
            'GET': self.get,
            'PATCH': self.patch,
            'PUT': self.update,
        })

    def update(self, request, parameters):
        return self.context(request).update(
            self.serialize_body(request),
            parameters)

    def patch(self, request, parameters):
        return self.context(request).patch(
            self.serialize_body(request),
            parameters)

    def delete(self, request, parameters):
        return self.context(request).delete(parameters)

    def get(self, request, parameters):
        return self.context(request).get(parameters)


class BulkController(BaseController):
    def __init__(self, context):
        super(BulkController, self).__init__(context)
        self.dispatch.update({
            'DELETE': self.delete,
            'PATCH': self.patch,
            'POST': self.create,
            'PUT': self.update,
        })

    def create(self, request, parameters):
        return self.context(request).bulk_create(
            self.serialize_body(request), parameters)

    def update(self, request, parameters):
        return self.context(request).bulk_update(
            self.serialize_body(request), parameters)

    def patch(self, request, parameters):
        return self.context(request).bulk_patch(
            self.serialize_body(request), parameters)

    def delete(self, request, parameters):
        return self.context(request).bulk_delete(
            self.serialize_body(request), parameters)


class Router(object):
    BULK_ROUTE = '_bulk'

    def __init__(self, root, resource_tree):
        self.resource_tree = resource_tree
        self.root = root

    @staticmethod
    def pairwise(iterable):
        pair = []
        for i, obj in enumerate(iterable):
            if i % 2 == 1:
                pair.append(obj)
                yield tuple(pair)
                pair = []
            else:
                pair.append(obj)
        if pair:
            pair.append(None)
            yield tuple(pair)

    def route(self, request):
        path = request.path_info.split('/')
        if path[0] == '':
            path = path[1:]

        if not path and self.root:
            return self.root(request)
        elif not path:
            raise HTTPNotFound()

        parameters = OrderedDict()
        print list(self.pairwise(path))
        node = self.resource_tree
        for resource_name, id_ in self.pairwise(path):
            print resource_name
            # break for bulk nodes
            if resource_name == self.BULK_ROUTE:
                return node(request, parameters, bulk=True)

            # get controller
            try:
                node = node[resource_name]
            except KeyError:
                raise HTTPNotFound()

            # parse parameters
            if id_ is not None:
                parameters[resource_name] = id_

        return node(request, parameters)


# TODO: ControllerFactory is a terrible name. Figure out something better.
class ControllerFactory(object):
    # class to manage accessing object
    CONTEXT = None
    # routing and parameter key
    NAME = None

    def __init__(self, resource_tree):
        self.resource_tree = resource_tree
        self.bulk_controller = BulkController(self.CONTEXT)
        self.resource_controller = ResourceController(self.CONTEXT)
        self.instance_controller = InstanceController(self.CONTEXT)

    def __call__(self, request, parameters, bulk=False):
    	LOG.debug('request: %s', request.params)
    	LOG.debug('parameters: %s', parameters)
    	LOG.debug('bulk: %s', bulk)
        if parameters[self.NAME] is None and bulk:
            return self.wrap(
                request,
                self.bulk_controller(request, parameters)
            )
        elif parameters[self.NAME] is None:
            return self.wrap(
                request,
                self.resource_controller(request, parameters)
            )
        elif bulk:
            raise HTTPNotFound(detail="Can't bulk operate on a resource instance")
        else:
            return self.wrap(
                request,
                self.instance_controller(request, parameters)
            )

    def wrap(self, request, response):
        if isinstance(response, Response):
            return response
        resp = Response(
            content_type=bytes(request.serialized_mime_type),
            charset=bytes(request.serialized_charset)
        )

        if isinstance(response, unicode):
            resp.text = response
        else:
            resp.text = request.serializer.dumps(response).decode(request.serialized_charset)

        return resp

    def __getitem__(self, key):
        return self.resource_tree[key]


class BaseDAO(object):
    def __init__(self, request):
        self.request = request

    def create(self, body):
        raise HTTPNotImplemented()

    def query(self, order='asc', offset=0, limit=None):
        raise HTTPNotImplemented()

    def update(self, id_, body):
        raise HTTPNotImplemented()

    def patch(self, id_, body):
        raise HTTPNotImplemented()

    def delete(self, id_):
        raise HTTPNotImplemented()

    def get(self, id_):
        raise HTTPNotImplemented()

    def bulk_create(self, body):
        raise HTTPNotImplemented()

    def bulk_update(self, body):
        raise HTTPNotImplemented()

    def bulk_patch(self, body):
        raise HTTPNotImplemented()

    def bulk_delete(self, body):
        raise HTTPNotImplemented()


class AwesomeRequest(Request):
    @property
    def serializer(self):
        return self.registry['serialization']['serializer']

    @property
    def serialized_mime_type(self):
        return self.registry['serialization']['mime']

    @property
    def serialized_charset(self):
        return self.registry['serialization']['charset']


class Application(object):
    RESOURCE_TREE = None
    ROOT = None

    def __init__(self, app_config):
        self.router = Router(self.ROOT, self.RESOURCE_TREE)
        self.app_config = app_config

    @wsgify(RequestClass=AwesomeRequest)
    def __call__(self, request):
        request.registry = self.app_config
        try:
            return self.router.route(request)
        except HTTPException as exc:
            return exc
