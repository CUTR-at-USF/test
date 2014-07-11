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
		
# Route(Test) isValid, (car on walkway, bike rental, walk, drive, etc)
# RouteBus(Test)  valid # of bullrunner routes used, etc
# GTFS tests
 
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

	# XXX - # of stations, at least some have bikes available, stations are within coordinates
	# contains station

	
# MAIN CODE
	
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

# DISCOVER/LOAD PARAMS FROM CSV, spawn a new suite and generate a new report
def find_tests(path, tests):
	files=os.listdir(path)
	for f in files:
		if os.path.isdir(path + "/" + f) and f[0] != '.':			
			tmp = find_tests(path + "/" + f, [])
			if len(tmp) > 0: tests += tmp 
			continue
			
		if f.lower().endswith('.csv'):
			obj = {'file': path + "/" + f, 'result':False, 'suite':False}
			obj['suite'] = unittest.TestSuite()
			obj['result'] = unittest.TestResult()
			
			cls = path.split('/')[-1]
			
			if len(cls) > 0: 
				for m in globals(): # XXX tests namespace
					if hasattr(globals()[m], cls) or m == cls:
						obj['cls'] = globals()[m]
						tests.append(obj)
						break
				
	return tests

test_suites = find_tests(args.csv_path, [])

# read CSV and add all tests to suite
for s in test_suites:
			file = open(s['file'], 'r')
			reader = csv.DictReader(file)
			fn = reader.fieldnames
			for row in reader:
				row = dict(row.items() + p.items()) # WILL OVERRIDE CSV SETTINGS
				for k in row:
					if row[k][0] == '[': row[k] = ast.literal_eval(row[k])
	
				s['param'] = row
				s['suite'].addTests( s['cls'].add_with_param(s['cls'], row ) )

				'''
				s.addTests( OTPVersion.add_with_param(OTPVersion, {'major':1, 'minor':0}) )
				s.addTests( USFPlanner.add_with_param(USFPlanner, {'invalid_modes':['CAR'], 'fromPlace':'28.061239833892966%2C-82.41375267505644', 'toPlace':'28.06365404757197%2C-82.41353273391724', 'mode':'BICYCLE', 'maxWalkDistance':'750', 'arriveBy':'false', 'showIntermediateStops':'false'} ) )
				s.addTests( USFBikeRental.add_with_param(USFBikeRental, {}) ) #{'otp_url':'http://127.0.0.1/otp/'}) )
				'''

report_data = {}

for s in test_suites:				
	s['suite'].run(s['result'])

	tests = {'run':s['result'].testsRun, 'skip':len(s['result'].skipped), 'failed':len(s['result'].failures), 'errors':len(s['result'].errors)}
	for t in s['suite']: 
		tests[t.id().split('.')[-1]] = {'skipped':[], 'failed':[], 'errors':[]}

	for r in s['result'].errors:		
		tests[r[0].id().split('.')[-1]]['errors'].append( r[1] ) # strip().split('\n')[-1]
	
	for r in s['result'].failures:
		tests[r[0].id().split('.')[-1]]['failed'].append( r[1] ) # strip().split('\n')[-1]	

	for r in s['result'].skipped:		
		tests[r[0].id().split('.')[-1]]['skipped'].append( r[1] ) # strip().split('\n')[-1]	
		
	report_data[s['file']] = tests

print report_data	
sys.exit(0)

# REPORT

#r = self.report_template.render(test_suites=self.test_suites, test_errors=self.has_errors())

	
sys.exit(0)

		
class TrimetTest(CsvTest):
    """ Params for test, along with run capability -- Test object is typically built from a row in an .csv test suite 
    """

    def __init__(self, param_dict, line_number, date=None, args=None):
        """ Given the CSV file lines, and line number, read and setup the test		
		{
            OTP params:
              'From'
              'To'
              'Max dist'
              'Mode'
              'Optimize'
              'Service' - expects 'Saturday' or 'Sunday' or leave empty
              'Time'

            Test params:
              'Arrive by' - expects 'FALSE' if arrive by test should not be ran or leave empty
              'Depart by' - expects 'FALSE' if depart by test should not be ran or leave empty
              'Expected output'
              'Expected trip duration'
              'Expected trip distance'
              'Expected number of legs'

            
        """
        self.csv_line_number = line_number
        self.csv_params      = param_dict
        self.date            = date

        self.itinerary       = None
        self.otp_params      = ''
        self.is_valid        = True
        self.error_descript  = None
        self.result          = TestResult.FAIL

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
            self.expect_num_legs = self.get_param('Expected number of legs')

        self.planner_url = envvar('OTP_URL',  'http://localhost:8080/otp/')
        self.map_url = envvar('OTP_MAP_URL',  'http://localhost:8080/index.html')
        self.init_url_params()
        self.date = self.get_date_param(self.date)


    def get_param(self, name, def_val=None):
        ret_val = def_val
        try:
            p = self.csv_params[name]
            if p is not None and len(p) > 0:
                ret_val = p.strip()
        except:
            logging.warn("WARNING: '{0}' was not found as an index in record {1}".format(name, self.csv_params))

        return ret_val


    def did_test_pass(self):
        ret_val = False
        if self.result is not None and self.result is TestResult.PASS:
            ret_val = True
        return ret_val


    def append_note(self, note=""):
        self.help += " " + note 
   
    def test_otp_result(self, strict=True):
        """ regexp test of the itinerary output for certain strings
        """
        if self.itinerary == None:
            self.result = TestResult.FAIL if strict else TestResult.WARN
            self.error_descript = "test_otp_result: itinerary is null"
            logging.info(self.error_descript)
        else:
            if len(self.itinerary) < 1000:
                self.result = TestResult.FAIL if strict else TestResult.WARN
                self.error_descript = "test_otp_result: itinerary content looks small at " + str(len(self.itinerary)) + " characters."
                logging.warn(self.error_descript)
            else:
                self.error_descript = "test_otp_result: itinerary content size is " + str(len(self.itinerary)) + " characters."
                logging.info(self.error_descript)
                warn = False
                if self.expect_output is not None and len(self.expect_output) > 0:
                    regres = re.search(self.expect_output, self.itinerary)
                    if regres is None:
                        self.result = TestResult.FAIL if strict else TestResult.WARN
                        self.error_descript += "test_otp_result: couldn't find " + self.expect_output + " in otp response."
                        warn = True
                if self.expect_duration is not None and len(self.expect_duration) > 0:
                    durations = re.findall('<itinerary>.*?<duration>(.*?)</duration>.*?</itinerary>', self.itinerary) 
                    error = 0.2
                    high = float(self.expect_duration) * (1 + error)
                    low = float(self.expect_duration) * (1 - error)
                    for duration in durations:
                        if int(duration) > high or int(duration) < low:
                            self.result = TestResult.FAIL if strict else TestResult.WARN
                            self.error_descript += "test_otp_result: an itinerary duration was different than expected by more than {0}%.".format(error * 100)
                            warn = True
                            break
                if self.expect_num_legs is not None and len(self.expect_num_legs) > 0:
                    try:
                        values = [int(i) for i in self.expect_num_legs.split('|')]
                        if len(values) != 2:
                            raise ValueError
                        min_legs = values[0]
                        max_legs = values[1]
                        all_legs = re.findall('<itinerary>.*?<legs>(.*?)</legs>.*?</itinerary>', self.itinerary)
                        for legs in all_legs:
                            num_legs = len(re.findall('<leg .*?>', legs))
                            if num_legs > max_legs or num_legs < min_legs:
                                self.result = TestResult.FAIL if strict else TestResult.WARN
                                self.error_descript += "test_otp_result: an itinerary returned was not between {0} and {1} legs.".format(min_legs, max_legs)
                                warn = True
                                break
                    except ValueError:
                        self.error_descript += "expected number of legs test not in 'min|max' format."
                        warn = True
                if warn:
                    logging.warn(self.error_descript)

        return self.result


    def get_planner_url(self):
        return "{0}?submit&{1}".format(self.planner_url, self.otp_params)


    def get_map_url(self):
        purl = self.planner_url.split('/')[-1]
        return "{0}?submit&purl=/{1}&{2}".format(self.map_url, purl, self.otp_params)

    
    def get_bullrunner_url(self): # XXX
        return "http://usfbullrunner.com?submit&" + self.otp_params

    
    def init_url_params(self):
        """
        """
        self.otp_params = 'fromPlace={0}&toPlace={1}'.format(self.coord_from, self.coord_to)
        if self.coord_from == None or self.coord_from == '' or self.coord_to == None or self.coord_to == '':
            if self.coord_from != None or self.coord_to != None:
                self.error_descript = "no from and/or to coordinate for the otp url (skipping test) - from:" + str(self.coord_from) + ' to:' + str(self.coord_to)
                logging.warn(self.error_descript)
            self.is_valid = False
       
    def url_distance(self, dist=None):
        self.url_param('maxWalkDistance', dist, self.distance)

    def url_mode(self, mode=None):
        self.url_param('mode', mode, self.mode)

    def url_optimize(self, opt=None):
        self.url_param('optimize', opt, self.optimize)

    def url_arrive_by(self, opt="true"):
        self.url_param('arriveBy', opt, self.optimize)

    def url_time(self, time=None):
        self.url_param('time', time, self.time)

    def url_time_7am(self):
        self.url_param('time', '7:00am')

    def url_time_12pm(self):
        self.url_param('time', '12:00pm')

    def url_time_5pm(self):
        self.url_param('time', '5:00pm')

    def url_service(self, svc=None):
        """
        """
        pass
    
    def get_date_param(self, date):
        """ provide a default date (set to today) if no service provided...
        """


        if self.otp_params.find('date') < 0:
            if date is None:
                if self.service is None:
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                elif self.service == 'Saturday':
                    date = self.url_service_next_saturday()
                elif self.service == 'Sunday':
                    date = self.url_service_next_sunday()
                else:
                    date = datetime.datetime.now().strftime("%Y-%m-%d")
                    logging.warn("service param '{0}' not valid, using todays date.".format(self.service))
            
            self.url_param('date', date)
        return date


    def url_service_next_weekday(self):
        """
        """
        pass

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

    def url_service_next_month_weekday(self):
        """
        """
        pass

    def depart_by_check(self):
        if self.depart_by == 'FALSE':
            self.is_valid = False

    def arrive_by_check(self):
        if self.arrive_by == 'FALSE':
            self.is_valid = False


class TestSuite(object):
    """ url
    """

    def __init__(self, dir, file, date=None):
        """
        """
        self.file_path = dir + file
        self.name = file
        self.date = date
        self.params = []
        self.tests  = []
        self.failures = 0
        self.passes   = 0
        self.read()

    def read(self):
        """ read a .csv file, and save each row as a set of test params
        """
        file = open(self.file_path, 'r')
        reader = csv.DictReader(file)
        fn = reader.fieldnames
        for row in reader:
            self.params.append(row)

    @classmethod
    def prep_url(cls, t):
        t.url_distance()
        t.url_mode()
        t.url_optimize()
        t.url_time()

    def do_test(self, t, strict=True):
        self.prep_url(t)
        if t.is_valid:
            t.call_otp()
            time.sleep(1)
            t.test_otp_result(strict)
            self.tests.append(t);
            if t.result is TestResult.PASS:
                self.passes += 1
            elif t.result is TestResult.FAIL:
                logging.info("test_suite: this test failed " + t.get_planner_url() + "\n")
                self.failures += 1
            sys.stdout.write(".")

    def run(self):
        """ iterate the list of tests from the .csv files, run the test (call otp), and check the output.
        """
        logging.info("test_suite {0}: ******* date - {1} *******\n".format(self.name, datetime.datetime.now()))
        for i, p in enumerate(self.params):
            # TYPE XXX routers, planner, bike_rental
            # http://docs.opentripplanner.org/apidoc/0.11.0/resource_GeocoderResource.html
            print p
            continue
            t = Test(p, i+2, self.date)  # i+2 is the line number in the .csv file, accounting for the header
            t.depart_by_check()
            self.do_test(t)

            """ arrive by tests
            """
            t = Test(p, i+2, self.date)
            t.url_arrive_by()
            t.append_note(" ***NOTE***: arrive by test ")
            t.arrive_by_check()
            self.do_test(t, False)

    def print_test_urls(self):
        """ iterate the list of tests from the .csv files and print the URLs
        """
        for i, p in enumerate(self.params):
            t = Test(p, i+2, self.date)  # i+2 is the line number in the .csv file, accounting for the header
            t.depart_by_check()
            self.prep_url(t)
            url = t.get_planner_url()
            if t.is_valid:
                print url

            """ arrive by tests
            """
            t = Test(p, i+2, self.date)
            t.url_arrive_by()
            t.append_note(" ***NOTE***: arrive by test ")
            t.arrive_by_check()
            url = t.get_planner_url()
            if t.is_valid:
                print url


class TestRunner(object):
    """ Run .csv tests from ./tests/ by constructing a
        url to the trip planner, calling the url, then printing a report
    """

    def __init__(self, report_template=None, args=None, suites='./otpdeployer/suites/'):
		"""constructor builds the test runner
		"""
		self.dir = args.csv_path
		self.test_suites = self.get_test_suites(args.date, self.dir)
		
		if args.template_path is not None:
			self.report_template = Template(filename=args.template_path)

    @classmethod
    def get_test_suites(cls, date=None, dir='./otpdeployer/suites/'):
        test_suites = []
        files=os.listdir(dir)
        for f in files:
            if f.lower().endswith('.csv'):
                t = TestSuite(dir, f, date)
                test_suites.append(t)
        return test_suites

    def has_errors(self):
        ret_val = False
        for t in self.test_suites:
            if t.failures > 0 or t.passes <= 0:
                ret_val = True
                logging.info("test_suite {0} has {1} error(s) and {2} passes".format(t, t.failures, t.passes))
        return ret_val

    def run(self):
        """ execute tests
        """
        for ts in self.test_suites:
            ts.run()

    def print_test_urls(self):
        """ print test urls...
        """
        for ts in self.test_suites:
            ts.print_test_urls()

    def report(self):
        """ render a pass/fail report
        """
        r = self.report_template.render(test_suites=self.test_suites, test_errors=self.has_errors())
        return r


def runner(args):
    ''' main entry of the test runner
    '''
    date = args.date
    lev  = logging.INFO
    if args.debug is True:
        lev = logging.DEBUG
	
    logging.basicConfig(level=lev)
    
    t = TestRunner(args=args)
    t.run()
    r = t.report()

    if t.has_errors():
        print('There were errors')
    else:
        print('Nope, no errors')
   
    f = open(args.report_path, 'w')
    f.write(r)
    f.flush()
    f.close()


def stress(argv):
    date = None
    if len(argv) > 2:
        date = argv[1]

    test_suites = TestRunner.get_test_suites(date)
    for ts in test_suites:
        ts.print_test_urls()


def main(argv):

	
	if args.stress is True:			
		stress(argv)
	else:
		runner(args)

def xmain(argv):
    ''' test method for developing / debugging the suite.... 
    '''
    date = None
    if len(argv) > 1:
        date = argv[1]

    logging.basicConfig(level=logging.INFO)
    template = envvar('OTP_TEMPLATE', './otpdeployer/templates/good_bad.html')
    x = Test({
              'From' : '1',
              'To' : '1',
              'Max dist' : '1',
              'Mode' : '1',
              'Optimize' : '1',
              'Service' : '1',
              'Time' : '1',
       }, 1, date)
    print x.get_planner_url()
    print x.get_map_url()
    print x.get_bullrunner_url()

if __name__ == '__main__':
    main(sys.argv)
