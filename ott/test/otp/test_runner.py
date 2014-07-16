"""
CUTR-at-USF Mobullity OTP Test Suites

Usage:

Requirements:
mako

"""

import os
import sys
import time
import datetime
import logging
import traceback

import csv
import re
import socket
import urllib2
from mako.template import Template

import ast
import argparse
import unittest
import json

def envvar(name, defval=None, suffix=None):
    """ envvar interface -- TODO: put this in a utils api
    """
    retval = os.environ.get(name, defval)
    if suffix is not None:
        retval = retval + suffix
    return retval

class TestResult:
    FAIL=000
    WARN=333
    PASS=111

# from tests import * # import Test base class and other child classes

# CSVLoader to add_test()

_cache = {}
def cache_get(key):
	""" basic dict accessor for global _cache """
	
	if key in _cache: 
		return _cache[key]
	
	return None

def cache_set(key, val):
	""" basic dict setter for global _cache """
	
	# XXX save time for expiration
	
	_cache[key] = val
	
class Test(unittest.TestCase):
	"""
	Base class for unit tests
	
	inspired by: http://eli.thegreenplace.net/2011/08/02/python-unit-testing-parametrized-test-cases/
	"""
	def __init__(self, methodName="runTest", param=None):
		super(Test, self).__init__(methodName)
		self.param = param
			
	@staticmethod
	def add_with_param(class_name, param=None):
		loader = unittest.TestLoader()
		names = loader.getTestCaseNames(class_name)
		suite = unittest.TestSuite()
		for name in names:
			suite.addTest(class_name(methodName=name, param=param))
		return suite

class OTPTest(Test):
	"""
	Base class containing methods to interact with OTP Rest Endpoint
	"""

	def __init__(self, methodName='runTest', param=None):
		u = self.param['otp_url'] if 'otp_url' in self.param else "http://localhost:8080/otp/" 
		if hasattr(self, 'url'): self.url = u + self.url
		else: self.url = u
		
		super(OTPTest, self).__init__(methodName, param)
		
	def run(self, result=None):
		self.url = self.url + self.url_params(self.param)		
						
		self.call_otp(self.url)		
				
		super(OTPTest, self).run(result)
		
	def setResponse(self, type):
		""" Allow JSON or XML responses """
		self.type = type if type in ['json', 'xml'] else 'json'

	# XXX parse XML/JSON helpers ?
	
	def call_otp(self, url):
		""" 
		Calls the trip web service
        """

		if cache_get(self.url) is not None:
			self.otp_response = cache_get(self.url)
			self.response_time = 0		
		else:		
			self.otp_response = None
			try:
				start = time.time()
				socket.setdefaulttimeout(45) # XXX params ?
				req = urllib2.Request(url, None, {'Accept':'application/%s' % self.type})
				res = urllib2.urlopen(req)
				self.otp_response = res.read()
				res.close()
				end = time.time()
				self.response_time = end - start
			
				logging.info("call_otp: response time of " + str(self.response_time) + " seconds for url " + url)
				logging.debug("call_otp: OTP output for " + url)
				logging.debug(self.otp_response)
				
				cache_set(self.url, self.otp_response)
			except Exception as ex:
				self.fail(msg="{0} failed - Exception: {1}".format(url, str(ex)))
	
		self.assertLessEqual(self.response_time, 30, msg="%s took *longer than 30 seconds*" % url)

	# Basic tests for all OTP calls
	def test_result_not_null(self):
		self.assertNotEqual(self.otp_response, None, msg="{0} - result is null".format(self.url))
	
	def test_result_too_small(self):
		self.assertGreater(len(self.otp_response), 1000, msg="{0} - result looks small".format(self.url))
	
	
	# get_planner_url, get_map_url, get_bullrunner_url XXX
    
	def url_params(self, params):
		""" From query parameters, create OTP-compatible URL """
		url = []
				
		otp_params = ['address', 'bbox', 'fromPlace', 'toPlace', 'maxWalkDistance', 'mode', 'optimize', 'arriveBy', 'departBy', 'date', 'time', 'showIntermediateStops']
		for i in params:
			if i not in otp_params: continue
			url.append("{0}={1}".format(i, params[i]))
				
		return '&'.join(url)

	# XXX date - saturday, sunday
	# maxWalkDistance, mode, optimize, arriveBy, time (7a, 12, 5p), 	
	# XXX routers

	
# BEGIN TESTCASES #


class OTPVersion(OTPTest):
	""" Check /otp/ serverInfo endpoint for various information """
	
	def __init__(self, methodName='runTest', param=None):
		self.methodName = methodName		
		self.param = param
		super(OTPVersion, self).__init__(methodName, param)
		if methodName == 'test_result_too_small':
			setattr(self, 'test_result_too_small', unittest.case.expectedFailure(self.test_result_too_small)) # because serverInfo is a small result 

	def setUp(self):
		# can self.skipTest(reason) here
		pass
		
	def run(self, result=None):		
		self.setResponse("json")		
		super(OTPVersion, self).run(result)
	
	def test_version(self):
		if 'major' not in self.param or 'minor' not in self.param: self.skipTest("suppress")
		
		d = json.loads(self.otp_response)
				
		t = int(self.param['major']) == d['serverVersion']['major'] and int(self.param['minor']) ==  d['serverVersion']['minor']
			
		self.assertTrue(t, msg="OTP version mismatch - {0} != {1}".format("%d.%d" % (int(self.param['major']), int(self.param['minor'])), "%d.%d" % (d['serverVersion']['major'], d['serverVersion']['minor'])))
		
'''			
class USFGeocoder(OTPTest):
	"""
	Test the OTP Geocoder service returns correct coordinates

	Requires: OTP >= 0.11.x
	"""
	
	def __init__(self, methodName='runTest', param=None):
		self.url = "geocode?"
		self.param = param
		super(USFGeocoder, self).__init__(methodName, param)

	def run(self, result=None):
		self.setResponse("json")		
		super(USFGeocoder, self).run(result)
						
	# opentripplanner-geocoder/src/main/resources/org/opentripplanner/geocoder/application-context.xml

	def test_timeout(self):
		pass
		
	def test_exists(self):		
		pass
		
	def test_expect_value(self):
		print self.otp_response
		if 'expect_value' in self.param:
			pass
'''

			
class USFPlanner(OTPTest):
	""" Perform various tests on the OTP route planner """
	
	def __init__(self, methodName='runTest', param=None):
		self.url = "routers/default/plan?"
		self.param = param
		super(USFPlanner, self).__init__(methodName, param)
	
	def run(self, result=None):
		if 'fromPlace' not in self.param or 'toPlace' not in self.param: self.fail(msg="{0} missing to or from coordinates".format(self.url))
		
		if 'date' not in self.param or len(self.param['date']) <= 0:
			svc = self.param['service'] if 'service' in self.param else None
			if svc == 'Saturday':
				self.param['date'] = self.url_service_next_saturday()
			elif svc == 'Sunday':
				self.param['date'] = self.url_service_next_sunday()
			else:
				self.param['date'] = datetime.datetime.now().strftime("%Y-%m-%d")
		
		super(USFPlanner, self).run(result)

	def url_service_next_saturday(self):
		date = datetime.datetime.now()
		day = date.weekday()
		if day == 6:
			date = date+datetime.timedelta(days=6)
		else:
			date = date+datetime.timedelta(days=5-day)
		date = date.strftime("%Y-%m-%d")
		return date
        
	def url_service_next_sunday(self):
		date = datetime.datetime.now()
		day = date.weekday()
		date = date+datetime.timedelta(days=6-day)
		date = date.strftime("%Y-%m-%d")
		return date
		
	def test_expected_output(self):
		if 'expected_output' not in self.param: self.skipTest('suppress')
					                
		regres = re.search(self.param['expected_output'], self.otp_response)
		
		self.assertNotEqual(regres, None, msg="Couldn't find {0} in otp response.".format(self.param['expected_output']))
  
	def test_trip_duration(self):
		if 'duration' not in self.param: self.skipTest('suppress')
		
		durations = re.findall('<itinerary>.*?<duration>(.*?)</duration>.*?</itinerary>', self.otp_response) 
		error = 0.2
		high = float(self.param['duration']) * (1 + error)
		low = float(self.param['duration']) * (1 - error)
		for duration in durations:
			t = int(duration) < low or int(duration) > high
			self.assertFalse(t, msg="An itinerary duration was different than expected by more than {0}%.".format(error * 100))
		
	def test_trip_distance(self):
		if 'distance' not in self.param: self.skipTest('suppress')
		
		distances = re.findall('<itinerary>.*?<distance>(.*?)</distance>.*?</itinerary>', self.otp_response) 
		error = 0.2
		high = float(self.param['distance']) * (1 + error)
		low = float(self.param['distance']) * (1 - error)
		for distance in distances:
			t = int(distance) < low or int(distance) > high
			self.assertFalse(t, msg="An itinerary distance was different than expected by more than {0}%.".format(error * 100))
	
	def test_trip_num_legs(self):
		if 'num_legs' not in self.param: self.skipTest('suppress')
		
		legs = self.param['num_legs'].split("|")
		if len(legs) <> 2: raise ValueError("num_legs must be in min|max format")
		values = [int(i) for i in legs]
		
		min_legs = values[0]
		max_legs = values[1]
		all_legs = re.findall('<itinerary>.*?<legs>(.*?)</legs>.*?</itinerary>', self.otp_response)
		for legs in all_legs:
			num_legs = len(re.findall('<leg .*?>', legs))
			t = num_legs > max_legs or num_legs < min_legs
			self.assertFalse(t, msg="An itinerary returned was not between {0} and {1} legs.".format(min_legs, max_legs))

	def test_invalid_modes(self):
		""" if any mode is present in a leg from invalid_modes, this test fails """
		
		if 'invalid_modes' not in self.param: self.skipTest('suppress')

		all_modes = re.findall('<leg mode="(.*)" route', self.otp_response)
		bad = list(set(all_modes) & set(self.param['invalid_modes'])) # intersection
		
		self.assertEqual(len(bad), 0, msg="Invalid modes ({0}) found in itinerary.".format(', '.join(bad)))
		
		
	def test_no_errors(self):
		
		regres = re.findall("<error><id>(.*)</id>", self.otp_response)
		if len(regres) > 0: errnum = regres[0]
		else: errnum = ''
		
		self.assertEqual(len(regres), 0, msg="OTP returned error #{0}".format(errnum))
		
		
	# XXX optimize, time (depart/arrive)
	
	
	'''
        self.itinerary       = None
        self.coord_from      = self.get_param('From')
        self.coord_to        = self.get_param('To')
        self.distance        = self.get_param('Max dist')
        self.mode            = self.get_param('Mode')
        self.optimize        = self.get_param('Optimize')
        self.service         = self.get_param('Service')
        self.time            = self.get_param('Time')
        if self.time is not None and self.time.find(' ') > 0:
            self.time = self.time.replace(' ', '')
        self.help     = self.get_param('help/notes')
        self.expect_output   = self.get_param('Expected output')
        self.expect_duration = self.get_param('Expected trip duration')
        self.expect_distance = self.get_param('Expected trip distance')
        self.expect_num_legs = self.get_param('Expected number of legs')
        self.arrive_by       = self.get_param('Arrive by')
        self.depart_by       = self.get_param('Depart by')        
        if 'Expected number of legs' in param_dict:
            self.expect_num_legs = self.get_param('Expected number of legs'			
	'''
	
	def run(self, result=None):		
		self.setResponse("xml") 
		super(USFPlanner, self).run(result)
		
# RouteBus(Test)  valid # of bullrunner routes used, etc
# GTFS tests
# http://mobullity.forest.usf.edu:8088/trip-updates?debug
# http://mobullity.forest.usf.edu:8088/vehicle-positions?debug

class USFBikeRental(OTPTest):
	""" Perform various tests on bike_rental API """	
	
	def __init__(self, methodName='runTest', param=None):
		self.url = "routers/default/bike_rental?"
		self.param = param
		super(USFBikeRental, self).__init__(methodName, param)

	def run(self, result=None):		
		self.setResponse("json")		
		super(USFBikeRental, self).run(result)
		
	def test_not_empty(self):		
		d = json.loads(self.otp_response)
		self.assertGreater(len(d["stations"]), 0, msg="{0} - stations is empty".format(self.url))

	def test_bikes_available(self):
		pass
	
	def test_stations_coordinates(self):
		pass
		
	
# DISCOVER/LOAD PARAMS FROM CSV, spawn a new suite and generate a new report
def find_tests(path, tests):
	files=os.listdir(path)
	for f in files:
		if os.path.isdir(path + "/" + f) and f[0] != '.':			
			tmp = find_tests(path + "/" + f, [])
			if len(tmp) > 0: tests += tmp 
			continue
			
		if f.lower().endswith('.csv'):
			obj = {'file': path + "/" + f, "lines":[]}
			
			cls = path.split('/')[-1]
			
			if len(cls) > 0: 
				for m in globals(): # XXX tests namespace
					if hasattr(globals()[m], cls) or m == cls:
						obj['cls'] = globals()[m]
						tests.append(obj)
						break
				
	return tests

	
# MAIN CODE

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="OTP Test Suite")
	
	parser.add_argument('-o', '--otp-url', help="OTP REST Endpoint URL")
	parser.add_argument('-m', '--map-url', help="OTP Map URL")
	
	parser.add_argument('-t', '--template-path', help="Path to test suite template(s)")
	parser.add_argument('-c', '--csv-path', help="Path to test suite CSV file(s)")
	parser.add_argument('-r', '--report-path', help="Path to write test suite report(s)")
	#parser.add_argument('-b', '--base-dir', help="Base directory for file operations")
	
	parser.add_argument('--date', help="Set date for service tests")
	# XXX
	#parser.add_argument('-s', '--stress', action='store_true', help="Enable stress testing mode (XXX)")
	parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode")
	
	parser.set_defaults(
	otp_url=envvar('OTP_URL', 'http://localhost:8080/otp/'), 
	map_url=envvar('OTP_MAP_URL', 'http://localhost:8080/index.html'), 
	template_path=envvar('OTP_TEMPLATE', './templates/good_bad.html'), 
	csv_path=envvar('OTP_CSV_DIR', './suites/'),
	report_path=envvar('OTP_REPORT', './report/otp_report.html'))
	
	args = parser.parse_args(sys.argv[1:]) # XXX skip interpreter if given ... works on linux? 
	
	lev = logging.WARN # NOTSET?
	if args.debug: lev = logging.DEBUG
	
	logging.basicConfig(level=lev)
	
	# set base parameters for tests
	p = {'otp_url':args.otp_url}
	if args.date is not None: p['date'] = args.date
	
	test_suites = find_tests(args.csv_path, [])
	
	# read CSV and add all tests to suite
	for s in test_suites:
		file = open(s['file'], 'r')
		reader = csv.DictReader(file)
		fn = reader.fieldnames
		i = 0
		for row in reader:
			i += 1
			row = dict(row.items() + p.items()) # WILL OVERRIDE CSV SETTINGS
			for k in row:
				if row[k][0] == '[': row[k] = ast.literal_eval(row[k])

				obj = {}
				obj['suite'] = unittest.TestSuite()
				obj['result'] = unittest.TestResult()
				obj['csv_line_number'] = i
				obj['param'] = row
				obj['suite'].addTests( s['cls'].add_with_param(s['cls'], row ) )
				s['lines'].append( obj )
				
				'''
				s.addTests( OTPVersion.add_with_param(OTPVersion, {'major':1, 'minor':0}) )
				s.addTests( USFPlanner.add_with_param(USFPlanner, {'invalid_modes':['CAR'], 'fromPlace':'28.061239833892966%2C-82.41375267505644', 'toPlace':'28.06365404757197%2C-82.41353273391724', 'mode':'BICYCLE', 'maxWalkDistance':'750', 'arriveBy':'false', 'showIntermediateStops':'false'} ) )
				s.addTests( USFBikeRental.add_with_param(USFBikeRental, {}) ) #{'otp_url':'http://127.0.0.1/otp/'}) )
				'''

	report_data = {}
	failures = 0

	for s in test_suites:				
		if s['file'] not in report_data: report_data[s['file']] = {'run':0, 'skipped':{}, 'failures':{}, 'errors':{}}
		
		for line in s['lines']:
			line['suite'].run(line['result'])
	
			report_data[s['file']]['run'] += line['result'].testsRun
			desc = "%d (%s)" % (line['csv_line_number'], line['param']['description']) if 'description' in line['param'] else "%d" % line['csv_line_number']
			
			# strip().split('\n')[-1] to remove full traceback
			for r in line['result'].errors:		
				report_data[s['file']]['errors']["%s:%s" % (r[0].id().split('.')[-1], desc)] = r[1] 
		
			for r in line['result'].failures:
				report_data[s['file']]['failures']["%s:%s" % (r[0].id().split('.')[-1], desc)] = r[1]
	
			for r in line['result'].skipped:		
				report_data[s['file']]['skipped']["%s:%s" % (r[0].id().split('.')[-1], desc)] = r[1]
		
			failures += len(line['result'].failures)		
				
	
	# REPORT
	
	report_template = Template(filename=args.template_path)
	r = report_template.render(test_suites=report_data, all_passed = True if failures <= 0 else False)
	
	fp = open(args.report_path, "w")
	fp.write(r)
	fp.close()

	