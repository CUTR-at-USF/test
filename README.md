USF OpenTripPlanner Testing Framework
=====================================

Requirements:
=============
* mako
* Python 2.7+ (standard library - unittest, etc)

Usage:
======
python ott/test/otp/test_runner.py

usage: test_runner.py [-h] [-o OTP_URL] [-m MAP_URL] [-t TEMPLATE_PATH]
                      [-c CSV_PATH] [-r REPORT_PATH] [--date DATE] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -o OTP_URL, --otp-url OTP_URL
                        OTP REST Endpoint URL
  -m MAP_URL, --map-url MAP_URL
                        OTP Map URL
  -t TEMPLATE_PATH, --template-path TEMPLATE_PATH
                        Path to test suite template(s)
  -c CSV_PATH, --csv-path CSV_PATH
                        Path to test suite CSV file(s)
  -r REPORT_PATH, --report-path REPORT_PATH
                        Path to write test suite report(s)
  --date DATE           Set date for service tests
  -d, --debug           Enable debug mode

The following variables can also be set via _Environment Variables_:
* OTP_URL (default http://localhost:8080/otp/
* OTP_MAP_URL (default http://localhost:8080/index.html)
* OTP_TEMPLATE (default ./templates/good_bad.html)
* OTP_CSV_DIR (default ./suites/)
* OTP_REPORT (default ./report/otp_report.html)
	

Architecture:
=============

The framework currently uses the standard python unittest library to setup various suites and run a battery of tests with parameters specified by lines of a CSV file.

Those CSV files will be loaded from OTP_CSV_DIR/TestClassName/ (ex: OTP_CSV_DIR/USFPlanner/*.csv)
@TODO load the individual test classes from a different namespace (like tests/) to avoid polluting __main__

Each "Test Class" currently uses the "OTPTest" as a base to indicate REST-API calls into the OpenTripPlanner server referenced by OTP_URL, and therefore all will attempt to perform the same tests (test_result_not_null, and test_result_too_small) in addition to any the subclass(es) define.

Each test supports different parameters:

OTPVersion: Polls the /otp/ endpoint for server info 
* test_version: Accepts major, minor and checks serverInfo version for match

USFPlanner: Checks /otp/routers/default/planner and supports all standard OTP parameters
* test_expected_output: 'expected_output' regular expression assertNotEqual(None)
* test_trip_duration: Checks all returned itinerary durations are within range of 'duration' 
* test_trip_distance: Checks all returned itinerary distances are within range of 'distance'
* test_trip_num_legs: Checks all # of legs in returned itinerary are within min|max of 'num_legs' 
* test_invalid_modes: Checks all returned itinerary leg mode="" doesn't exist in 'invalid_modes'
* test_no_errors: Ensures no <error><id>.* is returned in response.
 
USFBikeRental: Checks /otp/routers/default/bike_rental
* test_not_empty: Checks that the stations list is not empty
* test_bikes_available: Checks at least one station has bikes available
* test_stations_coordinates: Checks no stations are outside a region (XXX)

@TODO USFGeocoder
@TODO USFPlannerBus
@TODO GTFS tests

Each CSV file can also specify the following to override defaults, but not command-line arguments:
* otp_url


