from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
from logging import getLogger
from os.path import isfile, basename
from collections import OrderedDict
import json

check_conf_items = ['enabled', 'name', 'type', 'data', 'pass_t', 'pass_d']
check_def = {'enabled': 0, 'name': '', 'type': 'none', 'data': '', 'pass_t': '', 'pass_d': ''}


class SupStr(str):
	""" string that supports minus operation """
	_empty = ''
	
	def __init__(self, string=_empty):
		super(SupStr, self).__init__(string)
		
	def __sub__(self, other):
		""" minus operation as remove substring """
		assert isinstance(other, str)
		return self.replace(other, self._empty)
	

class EnsList(list):
	""" list that supports minus and plus operations as in ensemble deprived and union """
	_empty = iter(())
	
	def __init__(self, iterable=_empty):
		super(EnsList, self).__init__(iterable)
	
	def __sub__(self, other):
		""" as deprived ensemble operation """
		res = self.__class__(self._empty)
		assert isinstance(other, list)
		for each in self:
			if each not in other:
				res.append(each)
		return res
	
	def __add__(self, other):
		""" as union ensemble operation """
		res = self.__class__(self._empty)
		assert isinstance(other, list)
		for each in self:
			if each not in other:
				res.append(each)
		for each in other:
			if each not in self:
				res.append(each)
		return res
	
	def filter(self, contains):
		""" returns only items of the list that contains a specific string """
		res = self.__class__(self._empty)
		for each in self:
			if contains in each:
				res.append(each)
		return res
	

class ConfigFileNotFound(IOError):
	pass


class AutoOrderedDict(OrderedDict):
	'Store items in the order the keys were last added, and create sorted dicts, from dicts and key order list'
	
	def __init__(self, a_dict=dict(), order_list=list()):
		super(AutoOrderedDict, self).__init__()
		if a_dict and order_list: # values in same order as the list of keys
			for each in order_list:
				if each in a_dict:
					self[each] = a_dict[each]
		elif a_dict and not order_list: # values in same "order" as the original dict
			for k, v in a_dict.iteritems():
				self[k] = v
		elif order_list and not a_dict: # order without values, save the order, init all value to None
			for each in order_list:
				self[each] = None
	
	def __setitem__(self, key, value):
		if key in self:
			del self[key]
		OrderedDict.__setitem__(self, key, value)


# imported and edited from https://github.com/Fclem/isbio2/blob/master/isbio/breeze/non_db_objects.py # ae7abac : 428
class ConfigObject(object):
	_not = "Class %s doesn't implement %s()"
	CONFIG_GENERAL_SECTION = 'DEFAULT'
	__config = None
	label = ''
	name = ''
	
	def __unicode__(self): # Python 3: def __str__(self):
		return '%s (%s)' % (self.label, self.name)
	
	def __init__(self, config_file, name='', label=''):
		self.config_file_path = config_file
		self.name = name
		self.label = label
	
	# clem 17/05/2016
	@property
	def log(self):
		return getLogger()
	
	# clem 27/05/2016
	def _load_config(self):
		""" Load the config file in a ConfigParser.SafeConfigParser object """
		config = SafeConfigParser()
		config.readfp(open(self.config_file_path))
		self.log.debug(
			'Config : loaded and parsed %s / %s ' % (basename(self.config_file_path), self.__class__.__name__))
		return config
	
	@property
	def config(self):
		""" auto loading and caching of the whole configuration object for this ConfigObject """
		if not self.__config: # instance level caching
			if isfile(self.config_file_path):
				self.__config = self._load_config()
			else:
				msg = 'Config file %s not found' % self.config_file_path
				self.log.error(msg)
				raise ConfigFileNotFound(msg)
		return self.__config
	
	# clem 27/05/2016
	def get_value(self, section, option):
		""" get a string value from the config file with error handling (i.e. config.get() )
		
		:param section: name of the section
		:type section: basestring
		:param option: name of the option value to get
		:type option: basestring
		:return: the option value
		:rtype: str
		:raise: self.ConfigParser.NoSectionError, AttributeError, self.ConfigParser.NoOptionError
		"""
		try:
			return self.config.get(section, option)
		except (NoSectionError, AttributeError, NoOptionError) as e:
			self.log.warning('While parsing file ')
			raise
	
	def get(self, property_name, section=None):
		""" get a string value from the config file with error handling (i.e. config.get() )

		:param property_name: name of the option value to get
		:type property_name: basestring
		:param section: name of the section
		:type section: basestring
		:return: the option value
		:rtype: str
		:raise: self.ConfigParser.NoSectionError, AttributeError, self.ConfigParser.NoOptionError
		"""
		if not section:
			section = self.CONFIG_GENERAL_SECTION
		return self.get_value(section, property_name)

	@property
	def sections(self):
		""" same as ConfigParser function except that it returns a custom list that supports - and + ensemble operation

		:rtype: EnsList
		"""
		return EnsList(self.config.sections())

	def _items(self, section, raw=False, x_vars=None):
		""" same as ConfigParser function except that it returns a custom list that supports - and + ensemble operation
		
		:type section: str
		:type raw: bool
		:type x_vars:
		:rtype: EnsList
		"""
		return EnsList(self.config.items(section, raw, x_vars))
		
	def section(self, section_name=CONFIG_GENERAL_SECTION):
		""" same as ConfigParser function except that it gives items of a specific section excluding those of DEFAULT

		:type section_name: str
		:rtype: EnsList
		"""
		exclude = self._items(self.CONFIG_GENERAL_SECTION) if section_name != self.CONFIG_GENERAL_SECTION else list()
		return self._items(section_name) - exclude

	def save(self):
		self.config.write(open(self.config_file_path, 'w'))
		

class Checkers(object):
	@classmethod
	def url(cls, check):
		assert isinstance(check, CheckObject)
		from networking import test_url
		return test_url(check.check_data)
	
	@classmethod
	def tcp(cls, check):
		pass


class CheckObject(object):
	_enabled = ''
	_name = ''
	_type = ''
	_data = ''
	_pass_t = ''
	_pass_d = ''
	_id = None
	
	_checker_dict = {'url': Checkers.url, 'tcp': Checkers.tcp}
	
	def __init__(self, a_tuple_list, res_id=None):
		assert isinstance(a_tuple_list, list)
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

	def check(self):
		if self.enabled:
			if self.check_type in self._checker_dict.keys():
				return self._checker_dict[self.check_type](self)
			else:
				print 'There is no %s checker' % self.check_type
		return False

	def __str__(self):
		return str(self.data_dict)


class MyConfig(ConfigObject):
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

	@property
	def checks_dict(self):
		""" return a dictionary of all the available checks """
		res = dict()
		for each in self.sections.filter(self.SECTION_CHECKS_UNIT_PREFIX):
			check_id = SupStr(each) - self.SECTION_CHECKS_UNIT_PREFIX
			res.update({check_id: CheckObject(self.section(each), check_id)})
		
		return res

	def show_checks(self):
		for k, v in self.checks_dict.iteritems():
			print k, ':', v
			
	def check_all(self, update=True):
		for k, v in self.checks_dict.iteritems():
			assert isinstance(v, CheckObject)
			if v.enabled:
				res = v.check()
				if update:
					print "update not implemented"
				print v.name, ':', res


check_def = AutoOrderedDict(check_def, check_conf_items)
conf = MyConfig()
BASE_END_POINT_URL = '/v1/pages/%s/' % conf.page_id


class HTTPMethods(enumerate):
	GET = 'GET'
	POST = 'POST'
	PATCH = 'PATCH'
	DELETE = 'DELETE'
	all = [GET, POST, PATCH, DELETE]


class StatusPageIoInterface(object):
	_conf = None
	
	COMPONENT_BASE_URL = 'components/%s.json'
	COMPONENTS_URL = 'components.json'
	
	def __init__(self, inst_conf=MyConfig()):
		self._conf = inst_conf
	
	# components/[component_id].json
	def send(self, endpoint, data=dict(), method=HTTPMethods.GET):
		""" send a query to the StatusPage.io api using conf.api_bas_url

		:type endpoint: str
		:type data: dict
		:type method: str
		"""
		import httplib, urllib, time
		ts = int(time.time())
		assert isinstance(data, dict)
		assert method in HTTPMethods.all
		params = urllib.urlencode(data)
		headers = { "Content-Type": "application/x-www-form-urlencoded", "Authorization": "OAuth " + self._conf.api_key }
		
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


def check_container(container_name):
	pass


def check_url(url):
	pass

interface = StatusPageIoInterface(conf)
