## USF OpenTripPlanner Testing Framework

#### Requirements:

* Python 2.7+ (standard library - unittest, etc)
* mako
* gdata-2.0.18 (https://code.google.com/p/gdata-python-client/downloads/list)
* oauth2client (https://pypi.python.org/pypi/oauth2client/1.2)

#### Usage:

python ott/test/otp/test_runner.py

```
usage: 
test_runner.py [-h] [-o OTP_URL] [-m MAP_URL] [-t TEMPLATE_PATH]
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
  --log-level LOG_LEVEL
                        Set log level (Accepted: CRITICAL, ERROR, WARNING
                        (default), INFO, DEBUG)
  --skip SKIP_CLASS     Comma-delimited list of test name(s) to skip  
```

The following variables can also be set via _Environment Variables_:
* OTP_URL (default http://localhost:8080/otp/
* OTP_MAP_URL (default http://localhost:8080/index.html)
* OTP_TEMPLATE (default ./templates/good_bad.html)
* OTP_CSV_DIR (default ./suites/)
* OTP_REPORT (default ./report/otp_report.html)
	

#### Architecture:

The framework currently uses the standard python unittest library to setup various suites and run a battery of tests with parameters specified by lines of a CSV file either locally or remotely.

_Local CSV_:
Those CSV files will be loaded from OTP_CSV_DIR/TestClassName/ (ex: OTP_CSV_DIR/USFPlanner/*.csv)
@TODO load the individual test classes from a different namespace (like tests/) to avoid polluting __main__

_Remote CSV_:
The framework also supports loading parameters from (one) remote google spreadsheet by using the -R and -U arguments.  Although there are URL endpoints to download a spreadsheet as a CSV: 
	
	https://docs.google.com/feeds/download/spreadsheets/Export?key=1f_CTDgQfey5mY1eMO03D7UZ8855D-mxHsfYfsA3c4Zw&exportFormat=csv
	
This does not readily support files with multiple sheets - you must find the "gid" of each sheet, and download each individually.  To find the GIDs, you need the XML data from:
	
	https://spreadsheets.google.com/feeds/worksheets/1f_CTDgQfey5mY1eMO03D7UZ8855D-mxHsfYfsA3c4Zw/private/full

Which I was not able to get working without a corresponding authorization token.  So, I decided to use the full gdata APIs to access the same data using the appropriate OAuth2 mechanisms. For the first run, it will launch a browser to the Google authorization url and redirect to a local url to receive the necessary access and refresh tokens.

Currently, the client_secrets.json is for an application created by me via http://code.google.com/apis/console.  Switching it to any other should be trivial: 
- OAuth Client ID for a "native/desktop" application.  No extra APIs need to be enabled.

 
Each "Test Class" currently uses the "OTPTest" as a base to indicate REST-API calls into the OpenTripPlanner server referenced by OTP_URL, and therefore all will attempt to perform the same tests (test_result_not_null, and test_result_too_small) in addition to any the subclass(es) define.

Each test supports different parameters:

#### OTPVersion: Polls the /otp/ endpoint for server info 

* test_version: Accepts major, minor and checks serverInfo version for match

#### USFPlanner: Checks /otp/routers/default/planner and supports all standard OTP parameters

* test_expected_output: 'expected_output' regular expression assertNotEqual(None)
* test_trip_duration: Checks all returned itinerary durations are within range of 'duration' 
* test_trip_distance: Checks all returned itinerary distances are within range of 'distance'
* test_trip_num_legs: Checks all # of legs in returned itinerary are within min|max of 'num_legs' 
* test_invalid_modes: Checks all returned itinerary leg mode="" doesn't exist in 'invalid_modes'
* test_mode_exists: Ensures at least one leg used 'mode'
* test_no_errors: Ensures no <error><id>.* is returned in response.
* test_use_preferred_bus_route: Ensure 'use_bus_route' is used at least once.
* test_max_legs: Ensure count of any given leg mode is <= 'max_legs'

@TODO specified 'mode' is respected
@TODO specified 'preferredRoutes' and unpreferred
@TODO optimize
@TODO bike triangle routing
@TODO wheelchair

#### USFBikeRental: Checks /otp/routers/default/bike_rental

* test_not_empty: Checks that the stations list is not empty
* test_bikes_available: Checks at least one station has bikes available
* test_stations_coordinates: Checks no stations are outside a region 

#### USFGeocoder: Checks /otp-geocoder/geocode (@NOTE GeocoderService.java is missing from 1.0.x)

* test_count: Ensure count > 0
* test_name: Ensure 'address' matches returned 'description'
* test_expect_location: Ensure 'location' lat,lng == result lat lng
* test_no_error: Ensure service does not return an error

#### USFGraphMetadata: Checks /otp/routers/default/metadata

* test_bounds: Ensure lowerLeft, upperRight Lat/Lng are within bounds of 'coords'
* test_transit_modes: Ensure 'modes' is in transitModes

#### USFRouters: Checks /otp/routers/default

* test_not_empty: Ensure 'polygon' returned isn't empty

#### USFTransit: Check /routers/default/transit API (@NOTE TransitIndex.java is missing in 1.0.x currently)



## OneBusAway:

#### GTFSTripUpdates: Check /trip-updates?debug

* test_trip_updates: Ensure some "entity {" property trees are returned

#### GTFSVehicleUpdates: Check /vehicle-positions?debug

* test_vehicles_available: Ensure some "entity {" property trees are returned


@TODO OSM data, leaflet, tiles?

Each CSV file can also specify the following to override defaults, but not command-line arguments:
* otp_url

Also, other tests (excluding itself) can be noted as a required dependency for any other given tests by specifying arguments in the following form:
req_CLASSNAME_testName  with the arguments defined XXX.

