import sys
import requests
import json
from requests.auth import HTTPBasicAuth
import urllib3
import pprint
import time
import yaml
import io
import os
from pathlib import Path
import argparse
import re

try:
    local_dir = os.path.dirname(os.path.realpath(__file__))
except Exception:
    local_dir = os.getcwd()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url = 'http://127.0.0.1:5000/'
ssh_api_gw = 'api/ssh_job'
username = 'admin'
password = 'cisco_gw'
api_key = '5544332233444'


def ssh_post(job):
    return requests.post(base_url + ssh_api_gw, data=json.dumps({**{'job': job},
                                                                 **{'api_key': api_key}}),
                         auth=HTTPBasicAuth(username, password),
                         verify=False,
                         headers={"Content-Type": "application/json"}).json()


def write_results(results_dict, folder_path):
    save_dir = file_output_location(folder_path)
    for host_name, show_command_dict in results_dict.items():
        try:
            for command, show_command in show_command_dict.items():
                with open(str(Path(save_dir, '-'.join((host_name, command.replace(' ', '_'))))), 'w') as f:
                    f.write(results_dict[host_name][command])
        except Exception:
            print(f'ERROR {host_name}: {results_dict.get(host_name)}')


def parse_yaml(yaml_file):
    try:
        with open(yaml_file) as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(e)
        print('could not parse yaml file')
        sys.exit()


def parse_args(arg):
    if len(arg) > 1:
        print('too many file names')
        sys.exit()
    elif len(arg) == 0:
        print('please provide file name')
        sys.exit()
    else:
        yaml_arg = ''.join(map(str, arg))
        if not re.search('.yaml|.yml', yaml_arg):
            yaml_file = str(Path(local_dir, f'{yaml_arg}.yaml'))
        else:
            yaml_file = str(Path(local_dir, yaml_arg))
        return yaml_file


def file_output_location(file_path):
    if re.search(r'^/', file_path):
        if not os.path.isdir(file_path):
            os.system(f'mkdir {file_path}')
    else:
        file_path = str(Path(local_dir, file_path))
        if not os.path.isdir(file_path):
            os.system(f'mkdir {file_path}')
    return file_path


if __name__ == '__main__':
    yaml_location = parse_args(sys.argv[1:])
    yaml_file = parse_yaml(yaml_location)
    folder_path = yaml_file.get('output folder')
    yaml_file.pop('output folder')
    results_dict = ssh_post(yaml_file)
    write_results(results_dict, folder_path)
