from onlyinpgh.settings import to_abspath
import os, json

def open_test_json(appname,fn):
    relpath = os.path.join(appname,'test_json',fn)
    return open(to_abspath(relpath))

def load_test_json(appname,fn):
    with open_test_json(appname,fn) as f:
        return json.load(f)
