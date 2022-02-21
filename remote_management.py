import sys
import argparse
import requests
import json
from requests.auth import HTTPBasicAuth
import urllib3
import pprint
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url = 'http://127.0.0.1:5000/'
status_api = 'api/status'
start_api = 'api/start'
stop_api = 'api/stop'
username = 'admin'
password = 'cisco_gw'
api_key = '5544332233444'


def call_server(action):
    pprint.pprint(requests.post(base_url + action, data=json.dumps({'api_key': api_key}),
                                auth=HTTPBasicAuth(username, password), verify=False,
                                headers={"Content-Type": "application/json"}).json())


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-start', action='store_true', help='start all SSH sessions')
    parser.add_argument('-stop', action='store_true', help='stop all SSH sessions')
    parser.add_argument('-status', action='store_true', help='get SSH session status')
    args = parser.parse_args(args)
    if args.start and args.stop and args.status is False:
        print('please enter action')
        sys.exit()
    else:
        return args.start, args.stop, args.status


if __name__ == '__main__':
    start, stop, status = parse_args(sys.argv[1:])
    if start:
        call_server(start_api)
    if stop:
        call_server(stop_api)
    if status:
        call_server(status_api)
