from __future__ import unicode_literals
import logging

from collections import OrderedDict

from webob.exc import HTTPNotFound

LOG = logging.getLogger(__name__)


class Router(object):
    BULK_ROUTE = '_bulk'

    def __init__(self, root, resource_tree, navigation='flat'):
        self.resource_tree = resource_tree
        self.root = root

        nav_map = {
            'flat': self._nav_flat,
            'tree': self._nav_tree,
        }
        try:
            self.navigation = nav_map[navigation]
        except KeyError as nav_method:
            raise RuntimeError(
                'Invalid navigation method: {}'.format(nav_method)
            )

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

    def _nav_tree(self, path):
        bulk = False
        url_params = OrderedDict()
        node = self.resource_tree
        for resource_name, id_ in self.pairwise(path):
            # get controller
            try:
                node = node[resource_name]
            except KeyError:
                raise HTTPNotFound()

            # parse url_params
            if id_ == self.BULK_ROUTE:
                bulk = True
            elif id_ is not None:
                url_params[resource_name] = id_
        return node, url_params, bulk

    def _nav_flat(self, path):
        bulk = False
        url_params = OrderedDict()
        for resource_name, id_ in self.pairwise(path):
            # parse url_params
            if id_ == self.BULK_ROUTE:
                bulk = True
            elif id_ is not None:
                url_params[resource_name] = id_

        try:
            node = self.resource_tree[resource_name]
        except KeyError:
            raise HTTPNotFound()

        node

        return node, url_params, bulk

    def route(self, request):
        path = request.path_info.split('/')
        if path[0] == '':
            path = path[1:]

        if not path and self.root:
            return self.root(request)
        elif not path:
            raise HTTPNotFound()

        LOG.debug("route pairs: %s", list(self.pairwise(path)))
        node, url_params, bulk = self.navigation(path)
        return node, url_params, {'bulk': bulk}

    @classmethod
    def reverse(cls, request, context, resource):
        if resource is None:
            return request.path_info
        return '{}/{}'.format(request.path_info, context.get_pk(resource))
