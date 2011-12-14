To deploy this fork of the onlyinpgh code for replacing the data back end for
the old site, check out this fork and run ./manage syncdb. This will create
all the tables, including the oldevents tables that will store all events
from the site pre-12/14/11.

The included oldevents-12_14.sql.gz file can be dumped into this new schema
with a simple mysqldump command. It will fill the oldevents-app models. This
data should never have to be changed again after the initial import.
