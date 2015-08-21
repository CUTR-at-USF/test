# USF OpenTripPlanner Adding Testing cases instructions

This readme is intend to provide information solely about adding a new test case. For more information about how to use this test unit please refer to the main readme (It can be found here: https://github.com/CUTR-at-USF/test/tree/WIP-jmfield2#usf-opentripplanner-testing-framework).


## The test cases can be found in the following spreadsheet:

https://docs.google.com/spreadsheets/d/1f_CTDgQfey5mY1eMO03D7UZ8855D-mxHsfYfsA3c4Zw

## Adding a test case

Note: To add a new case the right to edit the spreadsheet is necessary (Link above).

**Example:**

```
$ python test_runner.py --add "http://mobullity.forest.usf.edu/index.html?module=planner&fromPlace=28.06914026483356%2C-82.40278244018555&toPlace=28.069272801561006%2C-82.40248203277588&time=6%3A09pm&date=07-23-2015&mode=TRANSIT%2CWALK&maxWalkDistance=1609.34&wheelchair=false&arriveBy=false&bannedRoutes=undefined&showIntermediateStops=true&itinIndex=0" --add-class=USFPlanner -R
```

The script ```test_runner.py``` need to be run with the following attribute:

```
--add ""
```

The itinerary link retrieved from the planner need to be inside of the quote. 
To copy the itinerary link from the planner, first plan your trip then in the bottom of the detail of this trip there should be a link named "Link to Itinerary", you only need to copy the url of this link.

```
--add-class=USFPlanner
```
This attribute specify which class the test will be added to. For now test can only be added to the class "USFPlanner".

```
-R 
```
This attributes makes test_runner load the CSV data remotely (from google sheets).  Without this, it will load local files from "suites/".

## Populating the various fields

Note: When the spreadsheet gets large, it may be confusing because some rows will reference tests but the column will still exist for other rows ... the current way to deal with this is just to add a single "-" in the column to "suppress" that test.


###The following field are automatically added by the --add command:

**Description of the test**

This field need to contain a brief description of the test.

column: desciption <br/>
value: a string of character

Note: this field is automatically filled up but it needs to be modify to something specific.
Note: If the test added is related to an issue present on the github please reference it like that: "(#X)"

**Coordinate for the path**

Start and end location of the trip to test.

columns: fromPlace **and** toPlace
value: two float separated by a coma (Latitude, Longitude)

**Check mode of transit**

This is currently both the OTP parameter and a JSON list of acceptable modes to be used for a given trip.

column: mode <br/>
value: name of the modes of transit comma-delimited 

**Check max walk distance**

An OTP Parameter that triggers an alert to be returned if a route exceeds this distance.

column: maxWalkDistance <br/>
value: float (meters)

**Check arriveBY**

OTP parameter that influences the routing decisions to try and accommodate arriving at a destination at a given time:


column: arriveBy <br/>
value: boolean or XX:XX YM (with X a number and Y A or P)

**Check Intermeediate stops**

This is an OTP parameter that adjusts the output of the trip planner - see http://dev.opentripplanner.org/apidoc/0.15.0/resource_PlannerResource.html

column: showIntermediateStops <br/>
value: boolean

**Time**

column: time <br/>
value: XX:XX YM (with X a number and Y A or P)

Note: this column will be automatically field by the the --add option but will add the time when the test is added which might not correspond to the value wanted in this column.
Note: The date column OTP parameter may be more influential in the routing process than time -- since some buses don't run on the weekend.

**otp_url**

This is to set the base URL to the OTP installation being tested. It can also be set from the command-line, or environment variables and these will override whatever is set in the CSV file.

column: otp_url <br/>
value: an url

###The following are automatically supressed (filled with '-') by the --add command:
Note:Technically all tests (specific) are automatically suppressed when using --add-url ... only the tests which don't require any parameter are not such as :
test_no_errors, test_result_not_null, test_result_too_small


**Check for invalid modes:**

This compares the SET of modes across all itineraries returned against the parameter and fails if any within the parameter are found.  Useful to e.g: make sure the planner doesn't tell someone to drive over a pedestrian path.

column: invalid_modes <br/>
value: JSON list  ['mode', 'mode2']

Note: Internally, this is just checks that the (set(a) & set(b)) intersection is empty.

**Check that a mode exists:**

The same as above, just ensure the intersection is NOT empty.

column: mode <br/>
value: JSON list or a single string

TODO: Make this not conflict with the planner request mode parameter?

**Check that a preferred bus route was used:**

Checks that at least one leg uses a route within parameter.

column: use_bus_route <br/>
value: JSON list or single string

**Check trip duration:**

If we want to check that the returned route duration was valid.

column: duration <br/>
value: integer (seconds? It's the same unit as what the trip planner gives for itinerary duration)

Internally, the code checks that at least one returned itinerary was within 20% of the duration parameter.

**Check trip distance:**

Same as above, except checking the total distance value returned is within 20% of the parameter.

column: distance <br/>
value: integer (seconds? It's the same unit as what the trip planner gives for itinerary duration)

**Check that the maximum walk distance was respected.**

Compares the 'walkDistance' returned in each itinerary with the parameter and asserts that it is less.

column: max_walk <br/>
value: integer

**Check expected output:**

Internally the test_expected_output function runs re.search(param['expected_output'], self.otp_response) and asserts that the return value was not None (that the regex matched)


column: expected_output <br/>
value: any regular expression suitable for re.search

**Check NOT expected output:**

The same as 'expected_output' except asserts that the regex was NOT found.

column: not_expected_output <br/>
value: any regular expression suitable for re.search


###The following are not yet present in the spreadsheet but are present in the code of the python script:

**Check the number of trip legs:**

Check that the number of legs within a given itinerary are within the specified range.  This can be good to check for cases where the route should e.g: dismount a bike and remount for crossing a street, etc.  Also for checking the number of bus routes (though it doesn't actually verify the mode here), or to make sure a long route is not giving one long WALK leg.  Although ALL 'results' must be within the range currently so if ANY ONE deviates the test will fail.

column: num_legs <br/>
value: min|max (2 integers separated by |)

**Check that legs doesn't exceed maximum:**

Count the total number of legs (across all itineraries) and assert it is less than the parameter.

column: max_legs <br/>
value: integer

TODO: Make this per_itinerary?


**Check that the arrival date was honored:**

Checks that the 'endTime' returned matches the parameter (hours, minutes, and seconds) for EACH itinerary.

column: arrive_time <br/>
value: H:M:S time

Required the 'arriveBy' OTP request parameter to provided.

**Check that trips depart at requested time:**

Same as above, except that 'startTime'

column: depart_time <br/>
value: H:M:S time

