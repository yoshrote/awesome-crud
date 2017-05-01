import mock
import unittest

from webob import Request
from webob import exc

class BaseControllerTest(unittest.TestCase):
	def setUp(self):
		from awesome_crud.base import BaseController
		self.context = mock.Mock()
		self.controller = BaseController(mock.Mock())

	def test_method_check(self):
		self.assertRaises(
			exc.HTTPMethodNotAllowed
			self.controller, Request.blank('/', method="FAKE"), {}
		)

	def test_options(self):
		response = self.controller.options(Request.blank('/'))
		self.assertEqual(response.allow, sorted(self.controller.dispatch.keys()))

