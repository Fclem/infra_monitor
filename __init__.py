#!/usr/bin/python
from utilz import *
from time import sleep
from threading import Thread
import json

__author__ = 'clement.fiere@helsinki.fi'
__date__ = '09/11/2016'

check_conf_items = ['enabled', 'name', 'type', 'data', 'pass_t', 'pass_d']
check_def = {'enabled': 0, 'name': '', 'type': 'none', 'data': '', 'pass_t': '', 'pass_d': ''}


#########
# ENUMs #
#########
class CheckStates(enumerate):
	OPERATIONAL = 'operational'
	DEGRADED = 'degraded_performance'
	PARTIAL_OUT = 'partial_outage'
	MAJOR_OUT = 'major_outage'


class HTTPMethods(enumerate):
	GET = 'GET'
	POST = 'POST'
	PATCH = 'PATCH'
	DELETE = 'DELETE'
	all = [GET, POST, PATCH, DELETE]


##################
# ACTUAL OBJECTS #
##################

class Checkers(object):
	""" the actual checks functions """
	@classmethod
	def url(cls, check):
		assert isinstance(check, CheckObject)
		from networking import test_url
		return test_url(check.check_data)
	
	@classmethod
	def tcp(cls, check):
		assert isinstance(check, CheckObject)
		from networking import test_tcp_connect
		spl = check.check_data.split(' ')
		host = spl[0]
		port = spl[1]
		return test_tcp_connect(host, port)
	
	@classmethod
	def ping(cls, check):
		assert isinstance(check, CheckObject)
		from networking import is_host_online
		return is_host_online(check.check_data)


class CheckObject(object): # Thread Safe
	""" a Thread Safe check object representing a CHECK config entry with its own check() function and status memory """
	_enabled = ''
	_name = ''
	_type = ''
	_data = ''
	_pass_t = ''
	_pass_d = ''
	_id = None
	_last_status = None
	_thread_lock = None
	ON_TEXT = 'ONLINE'
	OFF_TEXT = 'OFFLINE'
	UNK_TEXT = 'UNKNOWN'
	
	_checker_dict = {'url': Checkers.url, 'tcp': Checkers.tcp, 'ping': Checkers.ping}
	
	def __init__(self, a_tuple_list, res_id=None): # Thread Safe
		assert isinstance(a_tuple_list, list)
		self._thread_lock = AutoLock()
		with self._thread_lock as _:
			self.__dict__.update(check_def)
			for each in a_tuple_list:
				self.__dict__['_%s' % each[0]] = each[1] or check_def.get(each[0], '')
			self._id = res_id
	
	@property
	def id(self):
		if not self._id:
			self._id = hex(self.__hash__())
		return self._id
	
	@property
	def enabled(self):
		return self._enabled == '1'
	
	@property
	def name(self):
		return self._name
	
	@property
	def check_type(self):
		return self._type
	
	@property
	def check_data(self):
		return self._data

	@property
	def check_validation_type(self):
		return self._pass_t

	@property
	def check_validation_data(self):
		return self._pass_t
	
	@property
	def data_dict(self):
		a_dict = AutoOrderedDict({'id': self.id})
		for each in check_def:
			a_dict.update({each: self.__getattribute__(each)})
		return a_dict

	# clem 10/11/2016
	@property
	def last_status(self):
		# if not self._last_status:
		# 	self.check()
		return self._last_status
	
	# clem 10/11/2016
	def status_text(self, status):
		return self.ON_TEXT if status else self.OFF_TEXT if status is not None else self.UNK_TEXT

	# clem 10/11/2016
	@property
	def textual_status(self):
		return self.status_text(self.last_status)

	def check(self):  # Thread Safe
		status = False
		if self.enabled:
			if self.check_type in self._checker_dict.keys():
				status = self._checker_dict[self.check_type](self)
			else:
				print 'There is no "%s" checker' % self.check_type
		with self._thread_lock as _:
			self._last_status = status
		return self._last_status

	def __str__(self):
		return str(self.data_dict)


class MyConfig(ConfigObject):
	""" a concrete ConfigObject for this specific project """
	FILE_NAME = 'config.ini'
	
	KEY_API_KEY = 'api_key'
	KEY_PAGE_ID = 'page_id'
	KEY_API_BASE = 'api_base'
	
	SECTION_CHECKS_UNIT_PREFIX = 'CHECK_'
	
	def __init__(self):
		super(MyConfig, self).__init__(self.FILE_NAME, 'conf', 'general config for this monitor instance')
	
	@property
	def api_key(self):
		return self.get(self.KEY_API_KEY)
	
	@property
	def api_base_url(self):
		return self.get(self.KEY_API_BASE)
	
	@property
	def page_id(self):
		return self.get(self.KEY_PAGE_ID)


# TODO
class Component(object):
	"""
	ypkdj35tpnkz {u'status': u'operational', u'description': None, u'created_at': u'2016-10-28T09:34:54.006Z',
	u'updated_at': u'2016-11-10T13:56:54.417Z', u'position': 3, u'group_id': u'fmdlrkh6h12q', u'page_id':
	u'8g2t7p13fmp8', u'id': u'ypkdj35tpnkz', u'name': u'CAS'}
	"""


check_def = AutoOrderedDict(check_def, check_conf_items)
conf = MyConfig()
BASE_END_POINT_URL = '/v1/pages/%s/' % conf.page_id


class StatusPageIoInterface(object):
	""" Interface between configured checks and StatusPage.io components """
	_conf = None
	
	COMPONENT_BASE_URL = 'components/%s.json'
	COMPONENTS_URL = 'components.json'
	
	_check_cache = None
	
	def __init__(self, inst_conf=MyConfig()):
		self._conf = inst_conf
	
	def send(self, endpoint, data=None, method=HTTPMethods.GET):
		""" send a query to the StatusPage.io api using conf.api_bas_url

		:type endpoint: str
		:type data: dict
		:type method: str
		"""
		import httplib
		import urllib
		# import time
		# ts = int(time.time())
		data = data or dict()
		assert isinstance(data, dict)
		assert method in HTTPMethods.all
		params = urllib.urlencode(data)
		headers = {"Content-Type": "application/x-www-form-urlencoded", "Authorization": "OAuth " + self._conf.api_key}
		
		conn = httplib.HTTPSConnection(self._conf.api_base_url)
		conn.request(method, BASE_END_POINT_URL + endpoint, params, headers)
		response = conn.getresponse()
		
		print "Submitted %s to %s" % (data, endpoint)
		return response
	
	@property
	def _component_base_url(self):
		return self.COMPONENT_BASE_URL
	
	def _component_url(self, component_id):
		return self._component_base_url % component_id
	
	def component_update(self, component_id, data):
		return self.send(self._component_url(component_id), data, HTTPMethods.PATCH)

	def get_component_status(self, component_id):
		return json.load(self.send(self._component_url(component_id), method=HTTPMethods.GET))['status']
	
	@property
	def components_list(self):
		return json.load(self.send(self.COMPONENTS_URL))
	
	def show_components(self):
		a_list = self.components_list
		for each in a_list:
			print each['id'], each
	
	def _gen_config_generator(self, callbacks):
		""" fetch all the components from StatusPage.io and write then in the config file
		
		:param callbacks:
		:type callbacks: tuple[callable[str], callable[str, k, v], callable]
		"""
		assert isinstance(callbacks, tuple) and len(callbacks) == 3 and callable(callbacks[0]) and \
			callable(callbacks[1]) and callable(callbacks[2])
		
		header_callback = callbacks[0]
		inner_callback = callbacks[1]
		footer_callback = callbacks[2]
		
		a_list = self.components_list
		for each in a_list:
			sec_title = '%s%s' % (conf.SECTION_CHECKS_UNIT_PREFIX, each['id'])
			if sec_title not in conf.sections:
				header_callback(sec_title)
				for k, v in check_def.iteritems():
					inner_callback(sec_title, k, str(each.get(k, v)))
				footer_callback()
		conf.save()
	
	def show_config(self):
		""" fetch all the components from StatusPage.io and display then as ini structured data """
		def header(sec_title):
			print '[%s]' % sec_title
			
		def inner(_, k, val):
			print k, '=', val
			
		def footer():
			print ''
		
		self._gen_config_generator((header, inner, footer))
	
	def write_config(self):
		""" fetch all the components from StatusPage.io and write then in the config file """
		
		def header(sec_title):
			conf.config.add_section(sec_title)
		
		def inner(sec_title, k, val):
			conf.config.set(sec_title, k, str(val))
		
		def footer():
			pass
		
		self._gen_config_generator((header, inner, footer))
		conf.save()

	def update_check(self, check_instance, state):
		""" Update the status of one check, state has to be a value of CheckStates
		
		:type check_instance: CheckObject
		:type state: str
		:rtype:
		"""
		assert isinstance(check_instance, CheckObject)
		return self.component_update(check_instance.id, {'component[status]': state})
	
	# clem 10/11/2016
	def set_check_value(self, check_instance, value=False):
		""" Set the check component value to On or Off
		
		:type check_instance: CheckObject
		:type value: bool
		"""
		assert isinstance(check_instance, CheckObject)
		self.update_check(check_instance, CheckStates.OPERATIONAL if value else CheckStates.MAJOR_OUT)
	
	@property
	def checks_dict(self):
		""" return a dictionary of all the available checks """
		if not self._check_cache:
			res = dict()
			for each in self._conf.sections.filter(self._conf.SECTION_CHECKS_UNIT_PREFIX):
				check_id = SupStr(each) - self._conf.SECTION_CHECKS_UNIT_PREFIX
				res.update({check_id: CheckObject(self._conf.section(each), check_id)})
			self._check_cache = res
		return self._check_cache
	
	# TODO : make it a decorator
	def __check_apply(self, callback, threading=False):
		assert callable(callback)
		for key, check_instance in self.checks_dict.iteritems():
			if not threading:
				callback(key, check_instance)
			else:
				Thread(target=callback, args=(key, check_instance)).start()
	
	def show_checks(self):
		def sub(key, check_instance):
			print key, ':', check_instance
		self.__check_apply(sub)
	
	def check_all(self, update=False, threading=False):
		def update_check(check_instance, old_status, new_status):
			old_stat_text = check_instance.status_text(old_status)
			old_stat_text = TermColoring.fail(old_stat_text) if not old_status else TermColoring.ok_green(old_stat_text)
			
			new_stat_text = check_instance.textual_status
			new_stat_text = TermColoring.fail(new_stat_text) if not new_status else TermColoring.ok_green(new_stat_text)
			print '%s went from %s to %s' % (TermColoring.underlined(check_instance.name), old_stat_text, new_stat_text)
			self.set_check_value(check_instance, new_status)
		
		def sub(_, check_instance):
			assert isinstance(check_instance, CheckObject)
			if check_instance.enabled:
				old_status = check_instance.last_status
				new_status = check_instance.check()
				if update:
					if new_status != old_status:
						update_check(check_instance, old_status, new_status)
				else:
					print check_instance.name, ':', new_status
		
		self.__check_apply(sub, threading)
		
	def update_all(self):
		return self.check_all(True)
	
	# clem 10/11/2016
	def init_all_check_down(self):
		def sub(_, check_instance):
			assert isinstance(check_instance, CheckObject)
			# check_instance._last_status = False
			self.update_check(check_instance, CheckStates.PARTIAL_OUT)
		self.__check_apply(sub)


# clem 10/11/2016
class Watcher(object):
	""" a static class that monitors indefinitely all enabled checks and update them at a specific interval """
	_interface = StatusPageIoInterface(conf)
	# _interface.init_all_check_down()
	_counter = 0
	_wait_interval = 10. # in seconds
	_wait_resolution = .5 # in seconds
	_timer = _wait_interval
	
	@classmethod
	def _reset_timer(cls):
		cls._timer = cls._wait_interval
	
	@classmethod
	def _wait(cls):
		""" waiting function with incremental sleep duration of _wait_resolution and display of remaining time """
		cls._reset_timer()
		total_wait = cls._timer
		base_text = 'next update in %s sec ...' # % total_wait
		with IncPrint() as term:
			term.put(base_text % total_wait)
			while cls._timer > 0:
				term.put(base_text % cls._timer)
				sleep(cls._wait_resolution)
				cls._timer -= cls._wait_resolution
	
	@classmethod # TODO make a loop decorator
	def loop(cls):
		try:
			while True:
				cls._counter += 1
				print 'Checking round %s ...' % cls._counter
				Thread(target=cls._interface.update_all).start() # Thread maybe not so useful
				# cls._interface.update_all()
				cls._wait()
		except KeyboardInterrupt:
			print 'Exiting'
			return False

if __name__ == '__main__':
	# runs the watcher loop
	Watcher.loop()
