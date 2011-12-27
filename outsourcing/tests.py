
import logging
logging.disable(logging.CRITICAL)

# import all the test cases from the apitools subpackage
from onlyinpgh.outsourcing.apitools.tests import *

# import test cases from various subclasses
from onlyinpgh.outsourcing.subtests.identity import *
from onlyinpgh.outsourcing.subtests.places import *
from onlyinpgh.outsourcing.subtests.events import *
