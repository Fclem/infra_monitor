import socket
import subprocess as sp
from logging import getLogger

# imported from https://github.com/Fclem/isbio2/blob/master/isbio/utilz/networking.py # commit 6170526
__version__ = '0.1.1'
__author__ = 'clem'
__date__ = '27/05/2016'


def get_logger():
	return getLogger(__name__)


# clem on 20/08/2015
def is_host_online(host, deadline=5):
	""" Check if given host is online (whether it respond to ping)

	:param host: the IP address to test
	:type host: str
	:param deadline: the maximum time to wait in second (text format)
	:type deadline: str | int
	:rtype: bool
	"""
	res = sp.call(['ping', '-c', '3', '-i', '0.2', '-w', str(deadline), host], stdout=sp.PIPE)
	return res == 0


# clem 08/09/2016 moved here on 25/05/2016
def test_tcp_connect(host, port, timeout=2):
	""" Test if TCP can connect to target host on specified port

	:param host: ip address or FQDN of the target host
	:type host: str
	:param port: TCP port number to attempt connection to
	:type port: int | str
	:param timeout: connection timeout time in seconds
	:type timeout: int
	:return: if TCP connect is successful
	:rtype: bool
	:raises: socket.error or Exception
	"""
	try:
		s = socket.socket()
		if type(port) is not int:
			port = int(port)
		try:
			s.settimeout(timeout)
			s.connect((host, port))
			s.send('PING')
			get_logger().debug('TCP can connect to %s:%s' % (host, port))
			return True
		finally:
			s.close()
	except Exception:
		get_logger().debug('Failed connection to %s:%s' % (host, port))
		raise


# clem 29/04/2016
def get_free_port():
	"""
	:return: the number of a free TCP port on the local machine
	"""
	sock = socket.socket()
	sock.bind(('', 0))
	return sock.getsockname()[1]


# clem 12/10/2016
def get_http_response(target_url, timeout=5):
	""" Return the urllib2 response object from target url
	Warning : No exception management. Do it yourself


	:param target_url: url to reach or request object
	:type target_url: str | urllib2.Request
	:param timeout: time out in seconds
	:type timeout: int
	:return: the response object
	:rtype: urllib2.OpenerDirector
	:raises: (urllib2.URLError, urllib2.HTTPError)
	"""
	import urllib2
	
	opener = urllib2.build_opener()
	get_response = opener.open(target_url, None, timeout=timeout) or False
	
	return get_response


# clem 12/10/2016
def get_http_code(target_url, timeout=5):
	""" Return the HTTP code returned from target url


	:param target_url: url to reach or request object
	:type target_url: str | urllib2.Request
	:param timeout: time out in seconds
	:type timeout: int
	:return: the response HTTP code
	:rtype: int
	"""
	from urllib2 import URLError, HTTPError
	code = 520
	
	try:
		response = get_http_response(target_url, timeout)
		if hasattr(response, 'code'):
			code = response.code
	except (URLError, HTTPError) as e:
		get_logger().warning('%s : %s' % (e, target_url))
	
	return code


# clem 12/10/2016
def test_url(target_url, timeout=5):
	""" Tells whether or not the target_url is properly reachable (HTTP200 or HTTP302)


	:param target_url: url to reach or request object
	:type target_url: str | urllib2.Request
	:param timeout: time out in seconds
	:type timeout: int
	:return: does it return a proper HTTP code ?
	:rtype: bool
	"""
	return get_http_code(target_url, timeout) in [200, 302]
