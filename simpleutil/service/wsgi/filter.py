# -*- coding: UTF-8 -*-
import abc

import webob.dec
import webob.exc


class FilterBase(object):
    NAME = 'FilterBase'

    def __init__(self, application):
        self.application = application

    @abc.abstractmethod
    def process_request(self, request):
        """Called on each request.
        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.
        返回对象可以是Response实例
        webob将会直接直接调用这个Response实例的__call__方法
        返回对象可以是文本对象
        webob将通过req.Response类生成Response实例再调用__call__方法
        返回值不是None表明过滤失败
        """

    def process_response(self, request, response):
        """Do whatever you'd like to the response, based on the request."""
        return response

    @webob.dec.wsgify()
    def __call__(self, request):
        response = self.process_request(request)
        if response:
            return response
        response = request.get_response(self.application)
        return self.process_response(request, response)