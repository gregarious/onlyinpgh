import json, os

def load_test_json(fn):
    with open(os.path.join(os.path.dirname(__file__),'test_json',fn)) as f:
        return json.load(f)