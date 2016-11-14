from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
from os.path import isfile, basename
from collections import OrderedDict
from logging import getLogger
from threading import Lock
import sys


####################
# CUSTOMIZED TYPES #
####################
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


class AutoOrderedDict(OrderedDict):
	""" Store items in the order the keys were last added, and create sorted dicts, from dicts and key order list """
	def __init__(self, a_dict=None, order_list=list()):
		super(AutoOrderedDict, self).__init__()
		a_dict = a_dict or dict()
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
	
	def __setitem__(self, key, value, _=dict.__setitem__):
		if key in self:
			del self[key]
		OrderedDict.__setitem__(self, key, value)


# clem 10/11/2016
class SpecialEnum(object):
	# clem 11/11/2016
	@staticmethod # test
	def __visible_test(key): return not key.startswith('_')
	
	# clem 11/11/2016
	@staticmethod # test
	def __enum_test(key): return not key.startswith('_') and key.upper() == key
	
	# clem 11/11/2016
	@staticmethod # accessor
	def __get_all_filter(obj, key_pass_test=None):
		key_pass_test = key_pass_test if callable(key_pass_test) else lambda *_: True
		
		a_dict = dict()
		for key, value in obj.iteritems():
			if key_pass_test(key):
				a_dict.update({key: value})
		return a_dict
	
	# clem 11/11/2016
	@classmethod # proxy
	def all_dict(cls, my_test=None): return cls.__get_all_filter(cls.__dict__, my_test)
	
	# clem 11/11/2016
	@classmethod # proxy
	def enum_dict(cls): return cls.all_dict(cls.__visible_test)
	
	########
	# KEYS #
	########
		
	# clem 11/11/2016
	# @classmethod # proxy
	# def all_keys(cls): return cls.all_dict().keys()
	
	# clem 11/11/2016
	# @classmethod # proxy
	# def enum_keys(cls): return cls.enum_dict().keys()
	
	##########
	# VALUES #
	##########
	
	# clem 11/11/2016
	# @classmethod # proxy
	# def all_values(cls): return cls.all_dict().values()
	
	# clem 11/11/2016
	# @classmethod # proxy
	# def enum_values(cls): return cls.enum_dict().values()
	
	def __contains__(self, item): return item in self.enum_dict().values()


# clem 11/11/2016
class FunctionEnum(SpecialEnum):
	@classmethod # proxy
	def enum_functions(cls):
		a_dict = cls.enum_dict()
		for key, value in a_dict.iteritems():
			if type(value) in [staticmethod, classmethod]:
				a_dict[key] = value.__func__
		return a_dict
	
	
##################
# HELPER OBJECTS #
##################


# clem 10/11/2016
class AutoLock(object):
	""" Thread locking helper """
	
	def __init__(self):
		self._lock = Lock()
	
	def __enter__(self):
		self._lock.acquire()
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		self._lock.release()


# clem 10/11/2016
class IncPrint(object):
	""" incremental terminal writer helper """
	
	def __enter__(self):
		return self
	
	@staticmethod
	def put(text):
		sys.stdout.write('%s\r' % text)
		sys.stdout.flush()
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		sys.stdout.write('\033[2K\b\b')
		sys.stdout.flush()


# clem 10/11/2016 imported from https://github.com/Fclem/isbio2/blob/master/isbio/utilz/system.py # eac7b11 : 13
class TermColoring(enumerate):
	HEADER = '\033[95m'
	OK_BLUE = '\033[94m'
	OK_GREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	END_C = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'
	
	@classmethod
	def ok_blue(cls, text):
		return cls.OK_BLUE + str(text) + cls.END_C
	
	@classmethod
	def ok_green(cls, text):
		return cls.OK_GREEN + str(text) + cls.END_C
	
	@classmethod
	def fail(cls, text):
		return cls.FAIL + str(text) + cls.END_C
	
	@classmethod
	def warning(cls, text):
		return cls.WARNING + str(text) + cls.END_C
	
	@classmethod
	def header(cls, text):
		return cls.HEADER + str(text) + cls.END_C
	
	@classmethod
	def bold(cls, text):
		return cls.BOLD + str(text) + cls.END_C
	
	@classmethod
	def underlined(cls, text):
		return cls.UNDERLINE + str(text) + cls.END_C


################
# BASE CLASSES #
################

class ConfigFileNotFound(IOError):
	pass


# imported and edited from https://github.com/Fclem/isbio2/blob/master/isbio/breeze/non_db_objects.py # ae7abac : 428
class ConfigObject(object):
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
			self.log.warning('NotFound : %s' % str(e))
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
		# exclude = self._items(self.CONFIG_GENERAL_SECTION) if section_name != self.CONFIG_GENERAL_SECTION else list()
		# return self._items(section_name) - exclude
		return self._items(section_name)
	
	def save(self):
		self.config.write(open(self.config_file_path, 'w'))
