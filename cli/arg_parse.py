import argparse
import json
import os
from datetime import datetime
from typing import TypedDict, Callable

from utils.utils import get_project_root

CliActions = TypedDict("CliActions", {
    'init': Callable,
    'default': Callable
})

CLI_DESCR = "Dema Trading Engine"


def read_spec() -> list:
    spec_file_path = os.path.join(get_project_root(), "resources", "specification.json")

    with open(spec_file_path, "r", encoding='utf-8') as f:
        spec = f.read()
    return json.loads(spec)


def execute_for_args(actions: CliActions):
    config_spec = read_spec()
    parser = argparse.ArgumentParser(description=CLI_DESCR)
    parser.set_defaults(func=actions['default'])
    init_parser = parser.add_subparsers(dest="init").add_parser("init")
    init_parser.add_argument("dir", type=str, nargs='?', default=None)
    init_parser.set_defaults(func=actions['init'])

    for p in config_spec:
        cli = p.get("cli")
        if cli is None:
            continue
        t = spec_type_to_python_type(p["type"])
        parser.add_argument("-" + cli["short"], "--" + p["name"], type=t)

    args = parser.parse_args()
    args.func(args)


def spec_type_to_python_type(t: str):
    if t == "string":
        return str
    elif t == "int":
        return int
    elif t == "number" or t == "float":
        return float
    elif t == "dict":
        return dict
    elif t == "list":
        return list
    elif t == "bool":
        return str2bool
    elif t == "datetime":
        return datetime
    else:
        raise Exception


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('true', '1'):
        return True
    elif v.lower() in ('false', '0'):
        return False
    else:
        return None
