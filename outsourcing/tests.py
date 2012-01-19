
import logging
logging.disable(logging.CRITICAL)

# import all the test cases from the apitools subpackage
from onlyinpgh.outsourcing.apitools.tests import FacebookGraphTest, FactualResolveTest, GoogleGeocodingTest

# import test cases from various subclasses
from onlyinpgh.outsourcing.subtests.places import FactualResolutionTest, GoogleResolutionTest
from onlyinpgh.outsourcing.subtests.fbpages import PagePullingTest, OrgStorageTest, OrgImportingTest, PlaceStorageTest, PlaceImportingTest
from onlyinpgh.outsourcing.subtests.fbevents import EventStorageTest, EventImportingTest
from onlyinpgh.outsourcing.subtests.icalevents import ICalEventTest