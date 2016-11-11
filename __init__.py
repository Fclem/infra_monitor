#!/usr/bin/python
from utilz import *
from time import sleep
from threading import Thread
import json
import abc

__author__ = 'clement.fiere@helsinki.fi'
__date__ = '09/11/2016'

# clem 11/11/2016
__config_cache = None
CONFIG_FILE_NAME = 'config.ini'
DEFAULT_REFRESH = 30.


#########
# ENUMs #
#########
class CheckStates(SpecialEnum):
	OPERATIONAL = 'operational'
	DEGRADED = 'degraded_performance'
	PARTIAL_OUT = 'partial_outage'
	MAJOR_OUT = 'major_outage'


class HTTPMethods(SpecialEnum):
	GET = 'GET'
	POST = 'POST'
	PATCH = 'PATCH'
	DELETE = 'DELETE'


##################
# ACTUAL OBJECTS #
##################

class Checkers(FunctionEnum):
	""" the actual checks functions """
	@staticmethod
	def url(check):
		assert isinstance(check, CheckObject)
		from networking import test_url
		return test_url(check.check_data)
	
	@staticmethod
	def tcp(check):
		assert isinstance(check, CheckObject)
		from networking import test_tcp_connect
		spl = check.check_data.split(' ')
		host = spl[0]
		port = spl[1]
		return test_tcp_connect(host, port)
	
	@staticmethod
	def ping(check):
		assert isinstance(check, CheckObject)
		from networking import is_host_online
		return is_host_online(check.check_data)
	
	# clem 10/11/2016
	@staticmethod # TODO
	def docker(check):
		assert isinstance(check, CheckObject)
		# import DockerClient
		return False


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
	_check_def = None
	ON_TEXT = 'ONLINE'
	OFF_TEXT = 'OFFLINE'
	UNK_TEXT = 'UNKNOWN'
	
	_checker_dict = Checkers.enum_functions() # {'url': Checkers.url, 'tcp': Checkers.tcp, 'ping': Checkers.ping}
	
	def __init__(self, a_tuple_list, res_id=None): # Thread Safe
		assert isinstance(a_tuple_list, list)
		self._thread_lock = AutoLock()
		self._check_def = get_config().check_items_default_values_dict
		with self._thread_lock as _:
			self.__dict__.update(self._check_def)
			for each in a_tuple_list:
				self.__dict__['_%s' % each[0]] = each[1] or self._check_def.get(each[0], '')
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
		for each in self._check_def:
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
	DEFAULT_FILE_NAME = 'config.ini'
	config_file_name = ''
	
	KEY_API_KEY = 'api_key'
	KEY_PAGE_ID = 'page_id'
	KEY_API_URL = 'api_url'
	KEY_API_BASE = 'api_base'
	KEY_HTTP_MODE = 'http_mode'
	KEY_CONF_ITEMS = 'conf_items'
	KEY_ITEMS_PREFIX = 'items_prefix'
	KEY_REFRESH_INTERVAL = 'refresh_interval'
	
	SECTION_ITEMS_DEFAULTS_KEY = 'CONF_ITEMS_DEFAULTS'
	
	_check_items_defaults = dict()
	__config_cache = None
	
	def __init__(self, config_file_name=DEFAULT_FILE_NAME):
		self.config_file_name = config_file_name
		super(MyConfig, self).__init__(self.config_file_name, 'conf', 'general config for this monitor instance')
	
	@property
	def api_key(self): return self.get(self.KEY_API_KEY)
	
	@property
	def api_host_name(self): return self.get(self.KEY_API_BASE)
	
	@property
	def page_id(self): return self.get(self.KEY_PAGE_ID)
	
	@property
	def api_url_path_base(self): return self.get(self.KEY_API_URL)
	
	@property
	def http_mode(self): return self.get(self.KEY_HTTP_MODE)
	
	@property
	def conf_items_list(self): return self.get(self.KEY_CONF_ITEMS).split(' ')
	
	@property
	def section_items_prefix(self): return self.get(self.KEY_ITEMS_PREFIX)
	
	# 11/11/2016
	@property
	def refresh_interval(self): return float(self.get(self.KEY_REFRESH_INTERVAL)) or DEFAULT_REFRESH
	
	################
	# CUSTOM PROPS #
	################
	
	@property
	def check_items_default_values_dict(self):
		""" an AutoOrderedDict of default items values for checks """
		if not self._check_items_defaults:
			a_dict = AutoOrderedDict()
			for each in self.conf_items_list:
				a_dict.update({each: self.get(each, self.SECTION_ITEMS_DEFAULTS_KEY)})
			self._check_items_defaults = a_dict
		return self._check_items_defaults
	
	@property
	def use_ssl(self): return self.http_mode.lower() == 'https'
	
	@property
	def api_full_url_base(self):
		""" full url including host """
		return '%s/%s' % (self.api_host_name, self.api_url_path_base)
	

# clem 11/11/2016
# accessor
def get_config():
	global __config_cache
	if not __config_cache:
		__config_cache = MyConfig(CONFIG_FILE_NAME)
	return __config_cache


# clem 10/10/2016
class Component(object):
	"""
	ypkdj35tpnkz {u'status': u'operational', u'description': None, u'created_at': u'2016-10-28T09:34:54.006Z',
	u'updated_at': u'2016-11-10T13:56:54.417Z', u'position': 3, u'group_id': u'fmdlrkh6h12q', u'page_id':
	u'', u'id': u'', u'name': u'CAS'}
	"""
	_raw_data = dict()
	_status = ''
	_id = ''
	_name = ''
	
	def __init__(self, a_dict=None):
		if a_dict:
			self._raw_data = a_dict
			self._status = a_dict.get('status', '')
			self._id = a_dict.get('id', '')
			self._name = a_dict.get('name', '')
	
	@property
	def status(self):
		return self._status
	
	@status.setter
	def status(self, value):
		assert value in CheckStates()
		self._status = value
	
	@property
	def name(self):
		return self._name
	
	@property
	def id(self):
		return self._id
	
	@property
	def raw(self):
		return self._raw_data
	
	def __str__(self):
		return str(self.raw)


# clem 11/11/2016
class HTTPSenderAbstract(object):
	""" A basic HTTP sender meta Class that uses a MyConfig object """
	__metaclass__ = abc.ABCMeta
	_conf = None
	_check_cache = None
	_use_https = True
	
	def __init__(self, inst_conf, https=None):
		"""
		
		:type inst_conf: MyConfig
		:param https: force using or not using HTTPS, defaults to conf.use_ssl
		:type https: bool
		"""
		assert isinstance(inst_conf, MyConfig)
		self._conf = inst_conf
		if https is None:
			https = self._conf.use_ssl
		self._use_https = https
	
	# clem 11/11/2016
	def _sender(self, host, url, method=HTTPMethods.GET, data=None, use_auth=False):
		""" send a HTTP query to remote url

		:type host: str
		:type url: str
		:type method: str
		:type data: dict
		:type use_auth: bool
		"""
		import httplib
		import urllib
		
		assert method in HTTPMethods()
		
		data = data if isinstance(data, dict) else dict()
		params = urllib.urlencode(data)
		headers = dict()
		if data:
			headers.update({"Content-Type": "application/x-www-form-urlencoded"})
		if use_auth:
			headers.update({"Authorization": "OAuth " + self._conf.api_key})
		
		connector = httplib.HTTPSConnection if self._use_https else httplib.HTTPConnection
		conn = connector(host)
		conn.request(method, url, params, headers)
		response = conn.getresponse()
		
		proto, method = TermColoring.bold("HTTPS" if self._use_https else 'HTTP'), TermColoring.bold(method)
		status = TermColoring.bold(response.status)
		print "%s %s %s %s HTTP %s %s" % (proto, host + url, method, data, status, response.length)
		return response
	
	@abc.abstractmethod
	def _send(self, *args, **kwargs):
		""" should implement your own call proxy to self._sender """

	# clem 10/11/2016
	@property
	def _base_end_point_url(self):
		return self._conf.api_url_path_base
	
	# clem 10/11/2016
	@property
	def _host_url(self):
		return self._conf.api_host_name
	
	# clem 10/11/2016
	@abc.abstractmethod
	def _gen_url(self, url):
		""" would usually return self._base_end_point_url + url """


# clem 11/11/2016
class ServiceInterfaceAbstract(HTTPSenderAbstract):
	""" Interface between configured checks and a generic status reporting service """
	__metaclass__ = abc.ABCMeta
	__check_title_max_len = 0
	
	def __init__(self, inst_conf, https=None):
		super(ServiceInterfaceAbstract, self).__init__(inst_conf, https)
		
	@abc.abstractmethod
	def update_check(self, *args, **kwargs):
		""" Should implement your own way of updating or polling a check remote status using self._send """
	
	# clem 10/11/2016
	@abc.abstractmethod
	def set_check(self, check_instance, value=False):
		""" Should implement your own way of updating or polling a check based on a boolean value

		:type check_instance: CheckObject
		:type value: bool
		"""
	
	@property
	def check_def(self):
		""" a shortcut to the configuration AutoOrderedDict of default items values for checks """
		return self._conf.check_items_default_values_dict
	
	@property
	def checks_dict(self):
		""" :return: a dictionary of all the available checks as found in the config file """
		if not self._check_cache:
			res = dict()
			for each in self._conf.sections.filter(self._conf.section_items_prefix):
				check_id = SupStr(each) - self._conf.section_items_prefix
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
	
	# clem 10/11/2016
	@property
	def _check_title_max_len(self):
		""" :return: the lenght of the longest title from all checks """
		if not self.__check_title_max_len:
			self.__check_title_max_len = 0
			
			def sub(_, check_instance):
				if len(check_instance.name) > self.__check_title_max_len:
					self.__check_title_max_len = len(check_instance.name)
			
			self.__check_apply(sub)
		return self.__check_title_max_len
	
	def show_checks(self):
		def sub(key, check_instance):
			print key, ':', check_instance
		
		self.__check_apply(sub)
		
	# clem 11/11/2016
	def _print_check_stat(self, check_instance, old_status, new_status):
		""" neatly prints the check name with padding and its old and new state """
		def _rightly_padded_instance_name():
			format_str = '{:<%s}' % (self._check_title_max_len + 1 + len(TermColoring.underlined('')))
			return format_str.format(TermColoring.underlined(check_instance.name))
		
		old_stat_text = check_instance.status_text(old_status)
		old_stat_text = TermColoring.fail(old_stat_text) if not old_status else TermColoring.ok_green(old_stat_text)
		
		new_stat_text = check_instance.textual_status
		new_stat_text = TermColoring.fail(new_stat_text) if not new_status else TermColoring.ok_green(new_stat_text)
		print '%s : %s => %s' % (_rightly_padded_instance_name(), old_stat_text, new_stat_text)
	
	def check_all(self, update=False, threading=False):
		def _nop(*_):
			pass
		
		def _update_check(check_instance, old_status, new_status):
			self._print_check_stat(check_instance, old_status, new_status)
			self.set_check(check_instance, new_status)
		
		def sub(_, check_instance):
			assert isinstance(check_instance, CheckObject)
			if check_instance.enabled:
				old_status, new_status = check_instance.last_status, check_instance.check()
				
				calling = self._print_check_stat if not update else _update_check if new_status != old_status else _nop
				calling(check_instance, old_status, new_status)
		
		self.__check_apply(sub, threading)
	
	def update_all(self):
		return self.check_all(True)
	

class StatusPageIoInterface(ServiceInterfaceAbstract):
	""" Interface between configured checks and StatusPage.io components """
	COMPONENT_BASE_URL = 'components/%s.json'
	COMPONENTS_URL = 'components.json'
	
	_components_cache = None
	
	def __init__(self, inst_conf=get_config()):
		super(StatusPageIoInterface, self).__init__(inst_conf)
		_ = self.components_dict
		
	def _send(self, endpoint, data=None, method=HTTPMethods.GET):
		""" send a query to the StatusPage.io api using conf.api_bas_url
		
		:type endpoint: str
		:type data: dict
		:type method: str
		"""
		return self._sender(self._host_url, self._gen_url(endpoint), method, data, True)
	
	# clem 10/11/2016
	@property
	def _base_end_point_url(self): return self._conf.api_url_path_base
	
	# clem 10/11/2016
	@property
	def _host_url(self): return self._conf.api_host_name
	
	# clem 10/11/2016
	def _gen_url(self, url): return self._base_end_point_url + url
	
	###############################
	# REMOTE COMPONENTS SPECIFICS #
	###############################
	
	@property
	def _component_base_url(self): return self.COMPONENT_BASE_URL
	
	def _component_url(self, component_id): return self._component_base_url % component_id
	
	def component_update(self, component_id, data):
		return self._send(self._component_url(component_id), data, HTTPMethods.PATCH)
	
	# FIXME obsolete
	def get_component_status(self, component_id):
		return json.load(self._send(self._component_url(component_id), method=HTTPMethods.GET))['status']
	
	@property
	def _legacy_components_list(self): return json.load(self._send(self.COMPONENTS_URL))
	
	# clem 10/11/2016
	def _update_components(self):
		a_dict = dict()
		a_list = self._legacy_components_list
		for each in a_list:
			a_dict.update({each['id']: Component(each)})
		return a_dict
	
	# clem 10/11/2016
	@property
	def components_dict(self):
		if not self._components_cache:
			self._components_cache = self._update_components()
		return self._components_cache
	
	def show_components(self):
		a_list = self._legacy_components_list
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
		
		a_list = self._legacy_components_list
		for each in a_list:
			sec_title = '%s%s' % (self._conf.section_items_prefix, each['id'])
			if sec_title not in self._conf.sections:
				header_callback(sec_title)
				for k, v in self.check_def.iteritems():
					inner_callback(sec_title, k, str(each.get(k, v)))
				footer_callback()
		self._conf.save()
	
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
			self._conf.config.add_section(sec_title)
		
		def inner(sec_title, k, val):
			self._conf.config.set(sec_title, k, str(val))
		
		def footer():
			pass
		
		self._gen_config_generator((header, inner, footer))
		self._conf.save()
	
	###################
	# IMPLEMENTATIONS #
	###################

	def update_check(self, check_instance, status, force=False):
		""" Update the status of one check, state has to be a value of CheckStates
		
		:type check_instance: CheckObject
		:type status: str
		:type force: bool
		:rtype:
		"""
		assert isinstance(check_instance, CheckObject)
		a_component = self.components_dict.get(check_instance.id, Component())
		if force or a_component.status != status:
			response = self.component_update(check_instance.id, {'component[status]': status})
			if response.status == 200:
				a_component.status = status
			return response
		return False
	
	# clem 10/11/2016
	def set_check(self, check_instance, value=False):
		""" Set the check component value to On or Off
		
		:type check_instance: CheckObject
		:type value: bool
		"""
		assert isinstance(check_instance, CheckObject)
		return self.update_check(check_instance, CheckStates.OPERATIONAL if value else CheckStates.MAJOR_OUT)
	
	###############
	# SUP METHODS #
	###############
	
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
	_interface = StatusPageIoInterface(get_config())
	# _interface.init_all_check_down()
	_counter = 0
	_wait_interval = get_config().refresh_interval # in seconds
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
			return True
		# implicitly returns False on any other Exception as it will raise


def main():
	# runs the watcher loop
	return Watcher.loop()

if __name__ == '__main__':
	exit(0 if main() else 1)
else:
	conf = get_config()
