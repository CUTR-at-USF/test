"""
CUTR-at-USF Mobullity OTP Test Suites

Usage:

Requirements:
mako
gdata-2.0.18
oauth2client
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

import gdata.spreadsheets.client
import gdata.gauth


def envvar(name, defval=None, suffix=None):
    """ envvar interface -- TODO: put this in a utils api
    """
    retval = os.environ.get(name, defval)
    if suffix is not None:
        retval = retval + suffix
    return retval


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


class TestResultSuccess(unittest.TestResult):
    """
    TestResult class that also tracks successful tests
    """

    def __init__(self, *args, **kwargs):
        self.success = []

        super(TestResultSuccess, self).__init__(args, kwargs)

    def addSuccess(self, test):
        self.success.append(test)

class USFTestSuite(unittest.TestSuite):
    """
    Custom test suite that notates the status of the test on the testcase
    """

    def run(self, result, debug=False):

        super(USFTestSuite, self).run(result, debug)

        for test in self:
            if test in result.success: #and test.__unittest_skip__ == False:
                test.success = True
            else:
                test.success = False

# TestSuite <- TestCases  => TestResultSuccess

class Test(unittest.TestCase):
    """
	Base class for unit tests

	inspired by: http://eli.thegreenplace.net/2011/08/02/python-unit-testing-parametrized-test-cases/
	"""

    def __init__(self, methodName="runTest", param=None):
        super(Test, self).__init__(methodName)
        self.param = param
        self.methodName = methodName

    # XXX param req_TESTCLASS_TESTMETHOD and skip if fails

    @staticmethod
    def add_with_param(class_name, param=None):
        loader = unittest.TestLoader()
        names = loader.getTestCaseNames(class_name)

        suite = unittest.TestSuite()

        # req_TESTNAME_TESTMETHOD conditional dependencies
        reqsuite = unittest.TestSuite()
        reqres = unittest.TestResult()
        for key in param.keys():
            if key[0:4] <> "req_": continue
            depends = key.split("_")
            if depends[1] == class_name: continue  # try to prevent circular dependencies
            tmp_cls = find_test_class(depends[1])
            # class is depends[1] (cannot contain '_')
            methods = loader.getTestCaseNames(tmp_cls)
            for m in methods:
                if m <> param[key]: continue  # XXX should we do this, or run all tests?
                reqsuite.addTest(tmp_cls(methodName=m, param=param))

        for t in reqsuite:
            t.run(reqres)

        if reqres.testsRun > 0 and (reqres.errors > 0 or reqres.failures > 0):
            skip_tests = True
        else:
            skip_tests = False

        import copy

        for name in names:
            logging.info(class_name)

            tmp = class_name(methodName=name, param=copy.copy(param))
            tmp.set_dependency_check(skip_tests)
            suite.addTest(tmp)

        return suite

    def set_dependency_check(self, skip):
        self.skip_tests = skip

    def run(self, result=None):
        if hasattr(self, 'skip_tests') and self.skip_tests is True:
            self._addSkip(result, "dependency check failed")
        else:
            super(Test, self).run(result)

    def check_param(self, name):
        t = name in self.param and len(self.param[name]) > 0

        logging.info("check_param(%s) == %s" % (name, t))

        if t: return True

        return False


class UITest(Test):
    """ Selenium-based tests for client-side functions """

    def __init__(self, methodName='runTest', param=None):
        super(UITest, self).__init__(methodName, param)

    def run(self, result=None):
        super(UITest, self).run(result)


"""
# docs.seleniumhq.org/docs/03_webdriver.jsp
from selenium import webdriver
#browser = webdriver.ie.webdriver.WebDriver()
browser = webdriver.firefox.webdriver.WebDriver()
browser.get("http://yahoo.com/")
print browser.title
sys.exit(0)
"""

# waitForPageToLoad
# find_element_by_name, send_keys, submit()
# send_keys
# findElement, isDisplayed
# verifyText
# execute_script("return ..")



class OneBusAway(Test):
    """
	Test the gtfs-realtime-trip-updates API
	http://mobullity.forest.usf.edu:8088/trip-updates?debug
	http://mobullity.forest.usf.edu:8088/vehicle-positions?debug
	"""

    def __init__(self, methodName='runTest', param=None):
        self.url = self.param['otp_url'] if 'otp_url' in self.param else "http://localhost:8088/"

        super(OneBusAway, self).__init__(methodName, param)

    def run(self, result=None):

        self.call_api(self.url)

        super(OneBusAway, self).run(result)

    def call_api(self, url):
        """
		Calls the web service
        """

        logging.debug("call_api: %s" % url)

        if cache_get(url) is not None:
            self.api_response = cache_get(url)
            self.response_time = 0
        else:
            self.api_response = None
            try:
                start = time.time()
                socket.setdefaulttimeout(45)  # XXX params ?
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
                self.api_response = ""
                self.response_time = 0
            # self.fail(msg="{0} failed - Exception: {1}".format(url, str(ex)))

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
        if hasattr(self, 'url'):
            self.url = u + self.url
        else:
            self.url = u
        self.type = "xml"

        for i in self.param.keys():
            if type(self.param[i]) <> str: continue
            # In case some data is escaped, and some is not, first unquote, then quote
            self.param[i] = urllib2.quote(urllib2.unquote(self.param[i]))

        super(OTPTest, self).__init__(methodName, param)

    def run(self, result=None):
        self.url = self.url  # + self.url_params(self.param)

        self.call_otp(self.url)

        super(OTPTest, self).run(result)

    def setResponse(self, type):
        """ Allow JSON or XML responses """
        self.type = type if type in ['json', 'xml'] else 'json'

    def call_otp(self, url):
        """
		Calls the trip web service
        """

        logging.debug("call_otp: %s" % url)

        if cache_get(self.url) is not None:
            self.otp_response = cache_get(self.url)
            self.response_time = 0
        else:
            self.otp_response = None
            try:
                start = time.time()
                socket.setdefaulttimeout(45)  # XXX params ?
                req = urllib2.Request(url, None, {'Accept': 'application/%s' % self.type})
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
                self.otp_response = ""
                self.response_time = 0
            # self.fail(msg="{0} failed - Exception: {1}".format(url, str(ex)))

        self.assertLessEqual(self.response_time, 30, msg="%s took *longer than 30 seconds*" % url)

    # Basic tests for all OTP calls
    def test_result_not_null(self):
        self.assertNotEqual(self.otp_response, None, msg="{0} - result is null".format(self.url))

    def test_result_too_small(self):
        self.assertGreater(len(self.otp_response), 1000, msg="{0} - result looks small".format(self.url))

    def url_params(self, params):
        """ From query parameters, create OTP-compatible URL """
        url = []

        otp_params = ['address', 'bbox', 'fromPlace', 'toPlace', 'maxWalkDistance', 'mode', 'optimize', 'arriveBy',
                      'departBy', 'date', 'time', 'showIntermediateStops']
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

    # XXX sanity check the data ... start times not equal, at least X minutes apart, etc...


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
            setattr(self, 'test_result_too_small',
                    unittest.case.expectedFailure(self.test_result_too_small))  # because serverInfo is a small result

    def setUp(self):
        # can self.skipTest(reason) here
        pass

    def run(self, result=None):
        self.setResponse("json")
        super(OTPVersion, self).run(result)

    def test_version(self):
        if not self.check_param('major') or not self.check_param('minor'): self.skipTest("suppress")

        d = json.loads(self.otp_response)

        t = int(self.param['major']) == d['serverVersion']['major'] and int(self.param['minor']) == d['serverVersion'][
            'minor']

        self.assertTrue(t, msg="OTP version mismatch - {0} != {1}".format(
            "%d.%d" % (int(self.param['major']), int(self.param['minor'])),
            "%d.%d" % (d['serverVersion']['major'], d['serverVersion']['minor'])))


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

        self.url += self.url_params(self.param)

        super(USFGeocoder, self).run(result)

    def test_count(self):
        try:
            d = json.loads(self.otp_response)
            self.assertGreaterEqual(d['count'], 1, msg="{0} returned no geocode results".format(self.url))
        except:
            logging.debug(self.otp_response)
            self.fail("No JSON object returned - %s" % self.url)

    def test_name(self):
        if not self.check_param('address'): self.skipTest('suppress')

        try:
            d = json.loads(self.otp_response)
        except Exception as ex:
            logging.debug("\n\n%s = %s\n\n" % (str(ex), self.otp_response))
            self.fail("No JSON object returned - %s" % self.url)
            return

        t = False
        for res in d['results']:
            if res['description'] == urllib2.unquote(self.param['address']): t = True

        self.assertTrue(t, msg="{0} returned location(s) did not match ({1} != {2})".format(self.url, self.param['address'], ', '.join([urllib2.unquote(x['description']) for x in d['results']])))

    def test_no_error(self):
        try:
            d = json.loads(self.otp_response)
            self.assertEqual(d['error'], None, msg="{0} returned an error {1}".format(self.url, d['error']))
        except:
            logging.debug(self.otp_response)
            self.fail("No JSON object returned - %s" % self.url)

    def test_expect_location(self):
        if not self.check_param('location'): self.skipTest('suppress')

        failmsg = "{0} returned an unexpected location ({1}) - params:{2}"

        try:
            loc = urllib2.unquote(self.param['location']).split(',')
            d = json.loads(self.otp_response)
            for res in d['results']:
                # only check my exact address in case another was returned also
                if res['description'] <> self.param['address']: continue

                t = (str(res['lat']) == loc[0] and str(res['lng']) == loc[1])
                self.assertTrue(t, msg=failmsg.format(self.url, "%s,%s" % (res['lat'], res['lng']),
                                                      json.dumps(self.param)))

        except Exception as ex:
            logging.info("test_expect_location: %s" % str(ex))
            logging.info("test_expect_location: %s" % self.param)

            self.fail("%s url=%s" % (str(ex), self.url))


class USFGraphMetaData(OTPTest):
    """ Checks /otp/routers/default/metadata """

    def __init__(self, methodName='runTest', param=None):
        self.param = param
        self.url = "routers/default/metadata"
        super(USFGraphMetaData, self).__init__(methodName, param)
        if methodName == 'test_result_too_small':
            setattr(self, 'test_result_too_small',
                    unittest.case.expectedFailure(self.test_result_too_small))  # because serverInfo is a small result

    def run(self, result=None):
        self.setResponse("json")
        super(USFGraphMetaData, self).run(result)

    def test_transit_modes(self):
        if not self.check_param('modes'): self.skipTest('suppress')

        d = json.loads(self.otp_response)
        self.assertTrue(self.param['modes'] in d['transitModes'], msg="Transit mode not found in metadata")

    def test_bounds(self):
        """ test lowerLeft and upperRight against 'coords' """

        if not self.check_param('coords'): self.skipTest('suppress')

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
        if 'fromPlace' not in self.param or 'toPlace' not in self.param: self.fail(
            msg="{0} missing to or from coordinates".format(self.url))

        if 'date' not in self.param or len(self.param['date']) <= 0:
            svc = self.param['service'] if 'service' in self.param else None
            if svc == 'Saturday':
                self.param['date'] = self.url_service_next_saturday()
            elif svc == 'Sunday':
                self.param['date'] = self.url_service_next_sunday()
            else:
                self.param['date'] = datetime.datetime.now().strftime("%Y-%m-%d")

        self.url += self.url_params(self.param)

        super(USFPlanner, self).run(result)

    def url_service_next_saturday(self):
        date = datetime.datetime.now()
        day = date.weekday()
        if day == 6:
            date = date + datetime.timedelta(days=6)
        else:
            date = date + datetime.timedelta(days=5 - day)
        date = date.strftime("%Y-%m-%d")
        return date

    def url_service_next_sunday(self):
        date = datetime.datetime.now()
        day = date.weekday()
        date = date + datetime.timedelta(days=6 - day)
        date = date.strftime("%Y-%m-%d")
        return date

    def test_expected_output(self):
        if not self.check_param('expected_output'): self.skipTest('suppress')

        regres = re.search(self.param['expected_output'], self.otp_response)

        self.assertNotEqual(regres, None,
                            msg="Couldn't find {0} in otp response.".format(self.param['expected_output']))

    def test_not_expected_output(self):
        if not self.check_param('not_expected'): self.skipTest('suppress')

        regres = re.search(self.param['not_expected'], self.otp_response)

        self.assertEqual(regres, None, msg="Output was found in otp response.")

    def test_trip_duration(self):
        if not self.check_param('duration'): self.skipTest('suppress')

        durations = re.findall('<itinerary>.*?<duration>(.*?)</duration>.*?</itinerary>', self.otp_response)
        error = 0.2
        high = float(self.param['duration']) * (1 + error)
        low = float(self.param['duration']) * (1 - error)
        p = True

        for duration in durations:
            t = int(duration) < low or int(duration) > high
            if t: p = False

        self.assertTrue(p,
                        msg="An itinerary duration was different than expected by more than {0}%.".format(error * 100))

    def test_trip_distance(self):
        if not self.check_param('distance'): self.skipTest('suppress')

        distances = re.findall('<itinerary>.*?<distance>(.*?)</distance>.*?</itinerary>', self.otp_response)
        error = 0.2
        high = float(self.param['distance']) * (1 + error)
        low = float(self.param['distance']) * (1 - error)
        for distance in distances:
            t = int(distance) < low or int(distance) > high
            self.assertFalse(t, msg="An itinerary distance was different than expected by more than {0}%.".format(
                error * 100))

    def test_trip_num_legs(self):
        if not self.check_param('num_legs'): self.skipTest('suppress')

        legs = self.param['num_legs'].split("|")
        if len(legs) <> 2: raise ValueError("num_legs must be in min|max format")
        values = [int(i) for i in legs]

        min_legs = values[0]
        max_legs = values[1]
        all_legs = re.findall('<itinerary>.*?<legs>(.*?)</legs>.*?</itinerary>', self.otp_response)
        for legs in all_legs:
            num_legs = len(re.findall('<leg .*?>', legs))
            t = num_legs > max_legs or num_legs < min_legs
            self.assertFalse(t,
                             msg="An itinerary returned was not between {0} and {1} legs.".format(min_legs, max_legs))

    def test_invalid_modes(self):
        """ if any mode is present in a leg from invalid_modes, this test fails """

        if not self.check_param('invalid_modes'): self.skipTest('suppress')

        all_modes = re.findall('<leg mode="(.*?)" route', self.otp_response)
        bad = list(set(all_modes) & set(self.param['invalid_modes']))  # intersection

        self.assertEqual(len(bad), 0, msg="Invalid modes ({0}) found in itinerary.".format(', '.join(bad)))

    def test_mode_exists(self):
        """ Ensure 'mode' param exists in legs """

        if not self.check_param('mode'): self.skipTest('suppress')
        if type(self.param['mode']) <> list:
            l = [self.param['mode']]
        else:
            l = self.param['mode']

        all_modes = re.findall('<leg mode="(.*?)" route', self.otp_response)
        bad = list(set(all_modes) & set(l))  # intersection

        self.assertNotEqual(len(bad), 0, msg="Mode ({0}) NOT found in ({1}) itinerary.".format(self.param['mode'],
                                                                                               ','.join(all_modes)))

    def test_no_errors(self):
        """ Ensure no errors were returned """

        regres = re.findall("<error><id>(.*)</id>", self.otp_response)
        if len(regres) > 0:
            errnum = regres[0]
        else:
            errnum = ''

        self.assertEqual(len(regres), 0, msg="OTP returned error #{0}".format(errnum))

    # BUS CHECK
    def test_use_preferred_bus_route(self):
        """ Ensure a given route is chosen """

        if not self.check_param('use_bus_route'): self.skipTest('suppress')
        if not isinstance(self.param['use_bus_route'], list): self.param['use_bus_route'] = list(
            self.param['use_bus_route'])

        all_modes = re.findall('<leg mode="BUS" route="(.*?)"', self.otp_response)
        found = list(set(all_modes) & set(self.param['use_bus_route']))

        self.assertGreater(len(found), 0,
                           msg="Route did not use any of the preferred bus routes - %s not in %s - %s" % (
                               all_modes, self.param['use_bus_route'], self.url))

    # @TODO specified 'mode', 'preferredRoutes' and unpreferred

    def test_max_legs(self):
        """ Ensure # of modes are not excessive (multiple bus/car legs etc) """

        if not self.check_param('max_legs'): self.skipTest('suppress')

        all_modes = re.findall('<leg mode="(.*)" route', self.otp_response)

        # sum each mode and check against max_legs
        for m in all_modes:
            cnt = len(filter(lambda x: x == m, all_modes))

            self.assertLessEqual(cnt, self.param['max_legs'], msg="Route used too many legs for {0}".format(m))

    def test_arrive_by(self):
        # arriveBy=true
        # time.struct_time(tm_year=2014, tm_mon=7, tm_mday=7, tm_hour=7, tm_min=41, tm_sec=34, tm_wday=0, tm_yday=188, tm_isdst=-1)

        if not self.check_param('arrive_time'): self.skipTest('suppress')
        if self.param['arriveBy'] == "false": self.skipTest("did not request arrival time")

        all_times = re.findall('<endTime>(.*)<\/endTime>', self.otp_response)

        import time

        dt = time.strptime(self.param['arrive_time'], "%H:%M:%S")

        for m in all_times:
            mt = time.strptime(m[:-6], "%Y-%m-%dT%H:%M:%S")  # XXX timezone
            t = (mt["tm_hour"] == dt["tm_hour"]) and (mt["tm_min"] == dt["tm_min"]) and (mt["tm_sec"] == dt["tm_sec"])
            self.assertTrue(t, msg="{0} did not arrive at specified time: {1} != {2}".format(self.url,
                                                                                             self.param['arrive_time'],
                                                                                             m))

    def test_depart_at(self):
        # time, date, arriveBy=false 2014-07-07T07:41:34-04:00
        # time.struct_time(tm_year=2014, tm_mon=7, tm_mday=7, tm_hour=7, tm_min=41, tm_sec=34, tm_wday=0, tm_yday=188, tm_isdst=-1)
        if not self.check_param('depart_time'): self.skipTest('suppress')
        if self.param['arriveBy'] <> "false": self.skipTest("did not request departure time")

        all_times = re.findall('<startTime>(.*)<\/startTime>', self.otp_response)

        import time

        dt = time.strptime(self.param['depart_time'], "%H:%M:%S")

        for m in all_times:
            mt = time.strptime(m[:-6], "%Y-%m-%dT%H:%M:%S")  # XXX timezone
            t = (mt["tm_hour"] == dt["tm_hour"]) and (mt["tm_min"] == dt["tm_min"]) and (mt["tm_sec"] == dt["tm_sec"])
            self.assertTrue(t, msg="{0} did not start at specified time: {1} != {2}".format(self.url,
                                                                                            self.param['depart_time'],
                                                                                            m))

    def test_max_walk(self):
        """ Ensure maxWalkDistance is respected for route """

        if not self.check_param('max_walk'): self.skipTest('suppress')

        all_walk = re.findall('<walkDistance>(.*?)<\/walkDistance>', self.otp_response)

        t = False
        w = 0
        for m in all_walk:
            if m < self.param['max_walk']: t = True
            if w < m: w = m

        self.assertTrue(t, msg="{0} exceeded max_walk distance: {1} < {2}".format(self.url, self.param['max_walk'], w))


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
            self.assertGreater(row['bikesAvailable'], 0, msg="{0} - has no bikes available".format(row['name']))
            break  # at least one has to pass XXX

    def test_stations_coordinates(self):
        if not self.check_param('station_coordinates'): self.skipTest('suppress')

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
def find_tests(path, tests):
    files = os.listdir(path)
    for f in files:
        if os.path.isdir(path + "/" + f) and f[0] != '.':
            tmp = find_tests(path + "/" + f, [])
            if len(tmp) > 0: tests += tmp
            continue

        if f.lower().endswith('.csv'):
            cls = path.split('/')[-1]

            obj = {'file': path + "/" + f, "lines": [], 'name': cls}

            if len(cls) > 0:
                obj['cls'] = find_test_class(cls)
                if obj['cls'] is not None:
                    tests.append(obj)
                    break

    return tests


def find_test_class(cls):
    for m in globals():  # XXX tests namespace
        if hasattr(globals()[m], cls) or m.lower() == cls.lower():
            return globals()[m]
    return None


def load_csv_by_url(url, args="", parser=None):
    "Returns a list of suites from the specified spreadsheet URL."

    # Do OAuth2 stuff to create credentials object
    from oauth2client.file import Storage
    from oauth2client.client import flow_from_clientsecrets
    from oauth2client.tools import run_flow, argparser

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     parents=[argparser, parser], conflict_handler='resolve')
    flags = parser.parse_args(args)

    storage = Storage("creds.dat")
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = run_flow(
            flow_from_clientsecrets("client_secrets.json", scope=["https://spreadsheets.google.com/feeds"]), storage,
            flags)
    elif credentials.access_token_expired:
        import httplib2

        credentials.refresh(httplib2.Http())
        print "Refreshed"

    token = gdata.gauth.OAuth2TokenFromCredentials(credentials)
    gclient = gdata.spreadsheets.client
    g = gclient.SpreadsheetsClient()

    sheets = g.get_worksheets(url, auth_token=token)
    cnt = 0
    data = []

    for sheet in enumerate(sheets.entry):
        id = sheet[1].get_worksheet_id()

        logging.info("Sheet %s (%s)" % (sheet[1].title.text, id))

        cls = find_test_class(sheet[1].title.text)
        if cls is None: continue

        tmp = {"data": [], 'cls': cls, 'file': sheet[1].title.text, 'name': sheet[1].title.text}
        cnt = cnt + 1

        w = g.get_worksheet(url, id, auth_token=token)
        if w.row_count.text <= 0 or w.col_count.text <= 0: continue

        # have to get column names via get_cells because the listfeed auto-changes names
        fn = []
        col = []
        feed = g.get_cells(url, id, auth_token=token)
        for row in enumerate(feed.entry):
            if row[1].cell.text == "-": row[1].cell.text = ""  # workaround for get_cells() skipping blank cells
            if row[1].cell.row == "1":
                fn.append(row[1].cell.text)
            else:
                col.append(row[1].cell.text)

            if len(col) == len(fn):
                tmp["data"].append(dict(zip(fn, col)))
                col = []

        """
		feed = g.GetListFeed(url, id, auth_token=token)
		for row in enumerate(feed.entry):
			tmp["data"].append( dict(zip(fn, row[1].to_dict().values())) )
		"""

        data.append(tmp)

    print "%d sheets loaded" % cnt

    return data

# MAIN CODE

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OTP Test Suite")

    parser.add_argument('-o', '--otp-url', help="OTP REST Endpoint BASE URL (http://localhost:8080/otp/)")
    parser.add_argument('-m', '--map-url', help="OTP Map URL")

    parser.add_argument('-R', '--remote', action='store_true',
                        help="Enable fetching CSV parameters remotely from Google Spreadsheet (requires client_secrets.json)")
    parser.add_argument('-U', '--url', help="URL/Key to Google Spreadsheet with suite parameters (implies -R)")

    parser.add_argument('-t', '--template-path', help="Path to test suite template(s)")
    parser.add_argument('-c', '--csv-path', help="Path to test suite CSV file(s)")

    parser.add_argument('-r', '--report-path', help="Path to write test suite report(s)")
    # parser.add_argument('-b', '--base-dir', help="Base directory for file operations")

    parser.add_argument('--date', help="Set date for service tests")

    # XXX maybe disable cache for call_otp?
    # parser.add_argument('-s', '--stress', action='store_true', help="Enable stress testing mode (XXX)")

    parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode")
    parser.add_argument('--log-level',
                        help="Set log level (Accepted: CRITICAL, ERROR, WARNING (default), INFO, DEBUG) ")
    # XXX silent level?

    parser.add_argument('--skip', dest='skip_class', help="Comma-delimited list of test name(s) to skip")
    parser.add_argument('--only', dest='only_class', help="Comma-delimited list of test name(s) to use exclusively")

    parser.set_defaults(
        otp_url=envvar('OTP_URL', 'http://localhost:8080/otp/'),
        map_url=envvar('OTP_MAP_URL', 'http://localhost:8080/index.html'),
        template_path=envvar('OTP_TEMPLATE', './templates/good_bad.html'),
        csv_path=envvar('OTP_CSV_DIR', './suites/'),
        report_path=envvar('OTP_REPORT', './report/otp_report.html'),
        url="1f_CTDgQfey5mY1eMO03D7UZ8855D-mxHsfYfsA3c4Zw",  # Google doc key to USF file
        log_level="WARNING",
        skip_class=[None],
        only_class=[False])

    args = parser.parse_args(sys.argv[1:])  # XXX skip interpreter if given ... works on linux?

    # accept comma-delimited string of classes to skip
    if not isinstance(args.skip_class, list): args.skip_class = args.skip_class.lower().split(',')

    # accept comma-delimited string of classes to use
    if not isinstance(args.only_class, list):
        args.only_class = args.only_class.lower().split(',')
    elif args.only_class[0] is False:
        args.only_class = False

    # set log level
    try:
        lev = getattr(logging, args.log_level)
    except:
        print "Invalid Log Level '%s'" % args.log_level
        lev = logging.WARNING
    if args.debug: lev = logging.DEBUG

    logging.basicConfig(level=lev)

    # set base parameters for tests from environment
    p = {'otp_url': args.otp_url}
    if args.date is not None: p['date'] = args.date

    print "Loading test data...",

    # Load test parameters via google sheet
    if args.remote is True or args.url <> parser.get_default("url"):
        test_suites = load_csv_by_url(args.url, sys.argv[1:], parser)
    else:
        # Load tests from CSV files on disk
        test_suites = find_tests(args.csv_path, [])
        for s in test_suites:
            file = open(s['file'], 'r')
            reader = csv.DictReader(file)
            fn = reader.fieldnames
            i = 0
            s["data"] = []
            for row in reader: s["data"].append(row)
        print "Done"

    for key, s in enumerate(test_suites):
        i = 0
        s["lines"] = []
        for row in s['data']:
            i += 1

            # Skip test class if user chose to
            if s['name'].lower() in args.skip_class: continue

            # If user specified ONLY classes, skip anything not provided
            if args.only_class is not False and s['name'].lower() not in args.only_class:
                args.skip_class.append(s['name'].lower())
                continue

            # Override CSV parameters with cmd-line (unless they are defaults), and perform other initialization
            for k in p:
                if k in row and not p[k] == parser.get_default(k):
                    row[k] = p[k]  # XXX ENVVAR will now be 'default' and not override csv ...
                elif k not in row:
                    row[k] = p[k]

            # Convert strings into python literals where applicable (lists)
            for k in row:
                if len(row[k]) > 0 and row[k][0] == '[': row[k] = ast.literal_eval(row[k])

            # Create TestSuites from loaded TestCases

            obj = {}
            obj['suite'] = USFTestSuite()
            obj['result'] = TestResultSuccess()
            obj['csv_line_number'] = i
            obj['param'] = row

            # s.addTests( OTPVersion.add_with_param(OTPVersion, {'major':1, 'minor':0}) )
            obj['suite'].addTests(s['cls'].add_with_param(s['cls'], row))
            s['lines'].append(obj)

    # RUN TESTS

    report_data = {}
    failures = 0

    print "Running tests...",

    for s in test_suites:

        # Skip test class if user chose to
        if s['name'].lower() in args.skip_class: continue

        if s['file'] not in report_data: report_data[s['file']] = {'run': 0, 'total': 0,
                                                                    'skipped': {}, 'failures': {},
                                                                   'errors': {}, 'pass': {}, 'param': {}}

        for line in s['lines']:
            line['suite'].run(line['result'])

            if line['result'].testsRun == 0: continue

            report_data[s['file']]['run'] += line['result'].testsRun

            desc = "%d (%s)" % (line['csv_line_number'], line['param']['description']) if 'description' in line[
                'param'] else "%d" % line['csv_line_number']

            report_data[s['file']]['param'] = line['param']

            f = []
            for r in line['result'].errors:
                if not args.debug:
                    tmp = r[1].strip().split('\n')[-1]  # if not debug, only get last line (the assertionerror)
                else:
                    tmp = r[1]
                report_data[s['file']]['errors']["%s:%s" % (r[0].id().split('.')[-1], desc)] = tmp
                f.append(r)

            for r in line['result'].failures:
                if not args.debug:
                    tmp = r[1].strip().split('\n')[-1]  # if not debug, only get last line (the assertionerror)
                else:
                    tmp = r[1]
                report_data[s['file']]['failures']["%s:%s" % (r[0].id().split('.')[-1], desc)] = tmp
                f.append(r)

            for r in line['result'].skipped:
                if not args.debug:
                    tmp = r[1].strip().split('\n')[-1]  # if not debug, only get last line (the assertionerror)
                else:
                    tmp = r[1]
                report_data[s['file']]['skipped']["%s:%s" % (r[0].id().split('.')[-1], desc)] = tmp
                f.append(r)

            failures += len(line['result'].failures)

            # XXX
            for r in line['result'].expectedFailures:
                report_data[s['file']]['pass']["%s:%s" % (r[0].methodName, line['csv_line_number'])] = {"note":"Expected Failure"}

            #report_data[s['file']]['run'] -= len(line['result'].expectedFailures)
            #report_data[s['file']]['total'] -= len(line['result'].expectedFailures)

            tests = set()
            for r in line['suite']:
                tests.add(r.methodName)
                if r.success == False: continue

                # r.__class__.__name__
                report_data[s['file']]['pass']["%s:%s" % (r.methodName, line['csv_line_number'])] = {"param":r.param}

            report_data[s['file']]['total'] += line['result'].testsRun
            report_data[s['file']]['run'] -= len(line['result'].skipped)
            report_data[s['file']]['total'] -= len(line['result'].skipped)
            report_data[s['file']]['tests'] = tests


    print "Done"

    # REPORT

    # XXX try to sort tests by csv_line_number

    # XXX unique list of tests run

    # XXX show passing test details, stats ... also, hide skipped, failed, errors

    # XXX load template from google doc?

    # XXX save report to google doc/sheet?

    # simple_template.html

    from mako import exceptions

    report_template = Template(filename=args.template_path)

    try:
        r = report_template.render(test_suites=report_data, all_passed=True if failures <= 0 else False)
    except:
        r = exceptions.html_error_template().render()

    fp = open(args.report_path, "w")
    fp.write(r)
    fp.close()
