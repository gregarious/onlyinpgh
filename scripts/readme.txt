To clear data from all tabels before importing (must be in project root dir):
./scripts/clear_data.sh

To import data:
./manage.py runscript import_obid

### for greg:
things that this script could've used:
- location equality test
    - geocoding arguments in get are bad -- float equality problems
- resolver returning location from db instead of new one