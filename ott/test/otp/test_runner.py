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

		
class OneBusAway(Test):
	"""
	Test the gtfs-realtime-trip-updates API
	http://mobullity.forest.usf.edu:8088/trip-updates?debug
	http://mobullity.forest.usf.edu:8088/vehicle-positions?debug
	"""

	def __init__(self, methodName='runTest', param=None):
		u = self.param['otp_url'] if 'otp_url' in self.param else "http://localhost:8088/" 
		if hasattr(self, 'url'): self.url = u + self.url
		else: self.url = u
		
		super(OneBusAway, self).__init__(methodName, param)
		
	def run(self, result=None):
						
		self.call_api(self.url)		
				
		super(OneBusAway, self).run(result)
			
	def call_api(self, url):
		""" 
		Calls the web service
        """

		if cache_get(self.url) is not None:
			self.api_response = cache_get(self.url)
			self.response_time = 0		
		else:		
			self.api_response = None
			try:
				start = time.time()
				socket.setdefaulttimeout(45) # XXX params ?
				req = urllib2.Request(url, None, {}) 
				res = urllib2.urlopen(req)
				self.api_response = res.read()
				res.close()
				end = time.time()
				self.response_time = end - start
			
				logging.info("call_api: response time of " + str(self.response_time) + " seconds for url " + url)
				logging.debug("call_api: API output for " + url)
				logging.debug(self.api_response)
				
				cache_set(self.url, self.api_response)
			except Exception as ex:
				self.fail(msg="{0} failed - Exception: {1}".format(url, str(ex)))
	
		self.assertLessEqual(self.response_time, 30, msg="%s took *longer than 30 seconds*" % url)

	# Basic tests for all calls
	def test_result_not_null(self):
		self.assertNotEqual(self.api_response, None, msg="{0} - result is null".format(self.url))
	
	def test_result_too_small(self):
		self.assertGreater(len(self.api_response), 1000, msg="{0} - result looks small".format(self.url))
				
class OTPTest(Test):
	"""
	Base class containing methods to interact with OTP Rest Endpoint
	"""

	def __init__(self, methodName='runTest', param=None):
		u = self.param['otp_url'] if 'otp_url' in self.param else "http://localhost:8080/otp/" 
		if hasattr(self, 'url'): self.url = u + self.url
		else: self.url = u
		self.type = "xml"
		
		super(OTPTest, self).__init__(methodName, param)
		
	def run(self, result=None):
		self.url = self.url + self.url_params(self.param)		
						
		self.call_otp(self.url)		
				
		super(OTPTest, self).run(result)
		
	def setResponse(self, type):
		""" Allow JSON or XML responses """
		self.type = type if type in ['json', 'xml'] else 'json'

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
		
	def url_params(self, params):
		""" From query parameters, create OTP-compatible URL """
		url = []
				
		otp_params = ['address', 'bbox', 'fromPlace', 'toPlace', 'maxWalkDistance', 'mode', 'optimize', 'arriveBy', 'departBy', 'date', 'time', 'showIntermediateStops']
		for i in params:
			if i not in otp_params: continue
			url.append("{0}={1}".format(i, params[i]))
				
		return '&'.join(url)

	
# BEGIN TESTCASES #


class GTFSVehiclePositions(OneBusAway):

		def __init__(self, methodName='runTest', param=None):
			self.methodName = methodName		
			self.param = param
			super(GTFSVehiclePositions, self).__init__(methodName, param)
		
		def run(self, result=None):
			self.url = self.url + "vehicle-positions?debug"
			
			super(GTFSVehiclePositions, self).run(result)
			
		def test_vehicles_available(self):
			t = re.findall("entity {", self.api_response)
			
			self.assertGreater(len(t), 0, msg="{0} has no vehicle positions available".format(self.url))

class GTFSTripUpdates(OneBusAway):

		def __init__(self, methodName='runTest', param=None):
			self.methodName = methodName		
			self.param = param
			super(GTFSTripUpdates, self).__init__(methodName, param)
		
		def run(self, result=None):
			self.url = self.url + "trip-updates?debug"
			
			super(GTFSTripUpdates, self).run(result)
			
		def test_trips_available(self):
		
			t = re.findall("entity {", self.api_response)
			
			self.assertGreater(len(t), 0, msg="{0} has no trips available".format(self.url))			
										

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
			
			
class USFGeocoder(OTPTest):
	"""
	Test the OTP Geocoder service returns correct coordinates

	@TODO org.otp.geocoder.ws.geocoderserver missing from 1.0.x
	"""
	
	def __init__(self, methodName='runTest', param=None):		
		self.param = param
		self.url = "/otp-geocoder/geocode?"
		super(USFGeocoder, self).__init__(methodName, param)
		if methodName == 'test_result_too_small':
			setattr(self, 'test_result_too_small', unittest.case.expectedFailure(self.test_result_too_small)) 

	def run(self, result=None):
		self.setResponse("json")
		super(USFGeocoder, self).run(result)
						
	def test_count(self):		
		d = json.loads(self.otp_response)
		self.assertGreaterEqual(d['count'], 1, msg="{0} returned no geocode results".format(self.url))		
	
	def test_name(self):
		if 'address' not in self.param: self.skipTest('suppress')
		
		d = json.loads(self.otp_response)
		for res in d['results']:
			self.assertEqual(res['description'], self.param['address'], msg="{0} returned an address and not a USF building name".format(self.url))
		
	def test_no_error(self):
		d = json.loads(self.otp_response)
		self.assertEqual(d['error'], None, msg="{0} returned an error {1}".format(self.url, d['error']))
		
	def test_expect_location(self):
		if 'location' not in self.param: self.skipTest('suppress')

		loc = self.param['location'].split(',')
		d = json.loads(self.otp_response)
		for res in d['results']:
			t = (res['lat'] == loc[0] and res['lng'] == loc[1])
			self.assertTrue(t, msg="{0} returned an unexpected location".format(self.url))

			
class USFGraphMetaData(OTPTest):
	""" Checks /otp/routers/default/metadata """

	def __init__(self, methodName='runTest', param=None):		
		self.param = param
		self.url = "routers/default/metadata"
		super(USFGraphMetaData, self).__init__(methodName, param)		
		if methodName == 'test_result_too_small':
			setattr(self, 'test_result_too_small', unittest.case.expectedFailure(self.test_result_too_small)) # because serverInfo is a small result 

	def run(self, result=None):
		self.setResponse("json")
		super(USFGraphMetaData, self).run(result)
						
	def test_transit_modes(self):
		if 'modes' not in self.param: self.skipTest('suppress')
		
		d = json.loads(self.otp_response)
		self.assertTrue(self.param['modes'] in d['transitModes'], msg="Transit mode not found in metadata")
		
	def test_bounds(self):
		""" test lowerLeft and upperRight against 'coords' """

		if 'coords' not in self.param: self.skipTest('suppress')
		
		error = 0.2
		high = [float(self.param['coords'][0]) * (1 + error)]
		low = [float(self.param['coords'][0]) * (1 - error)]
		
		high[1] = float(self.param['coords'][1]) * (1 + error)
		low[1] = float(self.param['coords'][1]) * (1 - error)
		
		d = json.loads(self.otp_response)
		t = (row['lowerLeftLatitude'] >= low[0] and row['upperRightLatitude'] <= high[0])
		t = t and (row['lowerLeftLongitude'] >= low[1] and row['upperRightLongitude'] <= high[1])
			
		self.assertTrue(t, msg="Graph bounds not within coordinate range")
				

class USFRouters(OTPTest):
	""" Checks /otp/routers/default """

	def __init__(self, methodName='runTest', param=None):		
		self.param = param
		self.url = "routers/default"
		super(USFRouters, self).__init__(methodName, param)		
		if methodName == 'test_result_too_small':
			setattr(self, 'test_result_too_small', unittest.case.expectedFailure(self.test_result_too_small)) 

	def run(self, result=None):
		self.setResponse("json")
		super(USFRouters, self).run(result)

	def test_not_empty(self):
		d = json.loads(self.otp_response)
		self.assertNotEqual(len(d['polygon']), 0, msg="Graph polygon returned was empty")
		
'''		
class USFTransit(OTPTest):
	"""
	http://docs.opentripplanner.org/apidoc/0.11.0/resource_TransitIndex.html
	
	agencyIds, calendar, modes, routeData, routes, routesBetweenStops, routesForStop
	stopData, stopsByName, stopsInRectangle, stopsNearPoint, stopTimesForStop, stopTimesForTrip
	tripsAtPosition, variantForTrip
	"""	
	
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
		
	def test_mode_exists(self):
		""" Ensure 'mode' param exists in legs """
		if 'mode' not in self.param: self.skipTest('suppress')

		all_modes = re.findall('<leg mode="(.*)" route', self.otp_response)
		bad = list(set(all_modes) & set(self.param['mode'])) # intersection
		
		self.assertNotEqual(len(bad), 0, msg="Mode ({0}) NOT found in ({1}) itinerary.".format(self.param['mode'], ','.join(all_modes)))
		
	def test_no_errors(self):
		""" """
		regres = re.findall("<error><id>(.*)</id>", self.otp_response)
		if len(regres) > 0: errnum = regres[0]
		else: errnum = ''
		
		self.assertEqual(len(regres), 0, msg="OTP returned error #{0}".format(errnum))
		
	# BUS CHECK
	def test_use_preferred_bus_route(self):
		""" ensure a given route is chosen """
		if 'use_bus_route' not in self.param: self.skipTest('suppress')
		if not isinstance(self.param['use_bus_route'], list): self.param['use_bus_route'] = list(self.param['use_bus_route'])
		
		all_modes = re.findall('<leg mode="BUS" route="(.*)"', self.otp_response)
		found = list(set(all_modes) & set(self.param['use_bus_route']))
		
		self.assertGreater(len(found), 0, msg="Route did not use any of the preferred bus routes")
		
	# @TODO specified 'mode', 'preferredRoutes' and unpreferred
	
	def test_max_legs(self):
		""" ensure # of modes are not excessive (multiple bus/car legs etc) """
		if 'max_legs' not in self.param: self.skipTest('suppress')
		
		all_modes = re.findall('<leg mode="(.*)" route', self.otp_response)
		
		# sum each mode and check against max_legs
		for m in all_modes:
			cnt = len(filter(lambda x: x == m, all_modes))
					
			self.assertLessEqual(cnt, self.param['max_legs'], msg="Route used too many legs for {0}".format(m))	
	
	def test_arrive_by(self):
		# arriveBy=true
		# time.struct_time(tm_year=2014, tm_mon=7, tm_mday=7, tm_hour=7, tm_min=41, tm_sec=34, tm_wday=0, tm_yday=188, tm_isdst=-1)
		if 'arrive_time' not in self.param: self.skipTest('suppress')
		if self.param['arriveBy'] == "false": self.skipTest("did not request arrival time")
		
		all_times = re.findall('<endTime>(.*)<\/endTime>', self.otp_response)
		
		import time
		dt = time.strptime(self.param['arrive_time'], "%H:%M:%S")
		
		for m in all_times:			
			mt = time.strptime(m[:-6], "%Y-%m-%dT%H:%M:%S") # XXX timezone 
			t = (mt["tm_hour"] == dt["tm_hour"]) and (mt["tm_min"] == dt["tm_min"]) and (mt["tm_sec"] == dt["tm_sec"])
			self.assertTrue(t, msg="{0} did not arrive at specified time: {1} != {2}".format(self.url, self.param['arrive_time'], m))
				
	def test_depart_at(self):
		# time, date, arriveBy=false 2014-07-07T07:41:34-04:00
		# time.struct_time(tm_year=2014, tm_mon=7, tm_mday=7, tm_hour=7, tm_min=41, tm_sec=34, tm_wday=0, tm_yday=188, tm_isdst=-1)
		if 'depart_time' not in self.param: self.skipTest('suppress')
		if self.param['arriveBy'] <> "false": self.skipTest("did not request departure time")
		
		all_times = re.findall('<startTime>(.*)<\/startTime>', self.otp_response)
		
		import time
		dt = time.strptime(self.param['depart_time'], "%H:%M:%S")
		
		for m in all_times:			
			mt = time.strptime(m[:-6], "%Y-%m-%dT%H:%M:%S") # XXX timezone 
			t = (mt["tm_hour"] == dt["tm_hour"]) and (mt["tm_min"] == dt["tm_min"]) and (mt["tm_sec"] == dt["tm_sec"])
			self.assertTrue(t, msg="{0} did not start at specified time: {1} != {2}".format(self.url, self.param['depart_time'], m))
		
	def test_max_walk(self):
		""" Ensure maxWalkDistance is respected for route """
		
		if 'max_walk' not in self.param: self.skipTest('suppress')
		
		all_walk = re.findall('<walkDistance>(.*)<\/walkDistance>', self.otp_response)
				
		for m in all_walk:		
			self.assertLess(m, self.param['max_walk'], msg="{0} exceeded max_walk distance: {1} < {2}".format(self.url, self.param['max_walk'], m))
		
'''
@TODO optimize
@TODO bike triangle routing
@TODO wheelchair
'''		

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
		d = json.loads(self.otp_response)
		for row in d["stations"]:
			self.assertGreater(len(row['bikes']), 0, msg="{0} - has no bikes available".format(row['name']))
			break # at least one has to pass
			
	def test_stations_coordinates(self):
		if 'station_coordinates' not in self.param: self.skipTest('suppress')
		
		error = 0.2
		high = [float(self.param['station_coordinates'][0]) * (1 + error)]
		low = [float(self.param['station_coordinates'][0]) * (1 - error)]
		
		high[1] = float(self.param['station_coordinates'][1]) * (1 + error)
		low[1] = float(self.param['station_coordinates'][1]) * (1 - error)
		
		d = json.loads(self.otp_response)
		for row in d["stations"]:
			t = (row['lat'] >= low[0] and row['lat'] <= high[0])
			t = t and (row['lng'] >= low[1] and row['lng'] <= high[1])
			
			self.assertTrue(t, msg="{0} station not within coordinate range".format(row['name']))
		
	
# DISCOVER/LOAD PARAMS FROM CSV, spawn a new suite and generate a new report
def find_tests(path, tests, skip=[]):
	files=os.listdir(path)
	for f in files:
		if os.path.isdir(path + "/" + f) and f[0] != '.':			
			tmp = find_tests(path + "/" + f, [], skip)
			if len(tmp) > 0: tests += tmp 
			continue
			
		if f.lower().endswith('.csv'):
			obj = {'file': path + "/" + f, "lines":[]}
			
			cls = path.split('/')[-1]
			if cls.lower() in skip: continue
			
			if len(cls) > 0: 
				for m in globals(): # XXX tests namespace
					if hasattr(globals()[m], cls) or m.lower() == cls.lower():
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
	# XXX maybe disable cache for call_otp?
	#parser.add_argument('-s', '--stress', action='store_true', help="Enable stress testing mode (XXX)")
	parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode")
	parser.add_argument('--log-level', help="Set log level (Accepted: CRITICAL, ERROR, WARNING (default), INFO, DEBUG) ")
	# XXX silent level?
	parser.add_argument('--skip', dest='skip_class', help="Comma-delimited list of test name(s) to skip")
	
	parser.set_defaults(
	otp_url=envvar('OTP_URL', 'http://localhost:8080/otp/'), 
	map_url=envvar('OTP_MAP_URL', 'http://localhost:8080/index.html'), 
	template_path=envvar('OTP_TEMPLATE', './templates/good_bad.html'), 
	csv_path=envvar('OTP_CSV_DIR', './suites/'),
	report_path=envvar('OTP_REPORT', './report/otp_report.html'),
	log_level="WARNING",
	skip_class=[None])
	
	args = parser.parse_args(sys.argv[1:]) # XXX skip interpreter if given ... works on linux? 
	
	if not isinstance(args.skip_class, list): args.skip_class = args.skip_class.lower().split(',')
	
	try:
		lev = getattr(logging, args.log_level)
	except:
		print "Invalid Log Level '%s'" % args.log_level
		lev = logging.WARNING
	if args.debug: lev = logging.DEBUG
	
	logging.basicConfig(level=lev)
	
	# set base parameters for tests
	p = {'otp_url':args.otp_url}
	if args.date is not None: p['date'] = args.date
	
	test_suites = find_tests(args.csv_path, [], args.skip_class)	
	
	# read CSV and add all tests to suite
	for s in test_suites:
		file = open(s['file'], 'r')
		reader = csv.DictReader(file)
		fn = reader.fieldnames
		i = 0
		for row in reader:
			i += 1
			
			# ITERATE CMD-LINE ARGS AND ADD TO PARAM DICT -- SKIP OVERRIDING CSV WITH DEFAULTS
			for k in p:
				if k in row and not p[k] == parser.get_default(k): row[k] = p[k] # XXX ENVVAR will now be 'default' and not override csv ...
				elif k not in row: row[k] = p[k]

			for k in row:
				if row[k][0] == '[': row[k] = ast.literal_eval(row[k])

			obj = {}
			obj['suite'] = unittest.TestSuite()
			obj['result'] = unittest.TestResult()
			obj['csv_line_number'] = i
			obj['param'] = row
			# s.addTests( OTPVersion.add_with_param(OTPVersion, {'major':1, 'minor':0}) )
			obj['suite'].addTests( s['cls'].add_with_param(s['cls'], row ) ) 
			s['lines'].append( obj )
				
	report_data = {}
	failures = 0

	for s in test_suites:				
		if s['file'] not in report_data: report_data[s['file']] = {'run':0, 'skipped':{}, 'failures':{}, 'errors':{}}
		
		for line in s['lines']:
			line['suite'].run(line['result'])
				
			report_data[s['file']]['run'] += line['result'].testsRun
			desc = "%d (%s)" % (line['csv_line_number'], line['param']['description']) if 'description' in line['param'] else "%d" % line['csv_line_number']
			report_data[s['file']]['param'] = line['param']
			
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

	