import queue
import sys
import time
from threading import Lock, Thread
from random import randint
from netmiko import SSHDetect, ConnectHandler
import pprint
import os
from pathlib import Path
from configparser import ConfigParser
import argparse
import getpass
from flask import Flask, request
import ssh
import authentication_module

try:
    local_dir = os.path.dirname(os.path.realpath(__file__))
except Exception:
    local_dir = os.getcwd()

app = Flask(__name__)
app.config.from_object(__name__)
CONTENT = {'Content-Type': 'application/json'}
CERT = str(Path(local_dir, 'server.cert'))
KEY = str(Path(local_dir, 'server.key'))


def auth_cfg_import():
    if not os.path.isfile(str(Path(local_dir, 'auth_cfg.txt'))):
        print('auth_cfg.txt is missing')
        sys.exit()
    auth_config = ConfigParser()
    auth_config.read(str(Path(local_dir, 'auth_cfg.txt')))
    try:
        ssh_username = auth_config.get('auth_cfg', 'ssh_username')
    except Exception:
        ssh_username = None
    try:
        ssh_password = auth_config.get('auth_cfg', 'ssh_password')
    except Exception:
        ssh_password = None
    try:
        api_key = auth_config.get('auth_cfg', 'api_key')
    except Exception:
        api_key = None
    return ssh_username, ssh_password, api_key


def svr_cfg_import():
    if not os.path.isfile(str(Path(local_dir, 'server_cfg.txt'))):
        print('server_cfg.txt is missing')
        sys.exit()
    server_config = ConfigParser()
    server_config.read(str(Path(local_dir, 'server_cfg.txt')))
    try:
        https = server_config.get('server_cfg', 'https')
        print(f'from file {type(https)}')
        if https == 'False':
            https = False
        else:
            https = True
    except Exception:
        https = True
    try:
        interface = server_config.get('server_cfg', 'interface')
    except Exception:
        interface = None
    try:
        port = server_config.get('server_cfg', 'port')
    except Exception:
        port = 5000
    return https, interface, port


def setup(args):
    if len(args) > 0:
        parser = argparse.ArgumentParser()
        parser.add_argument('-auth_cfg', action='store_true', help='uses local cred file')
        parser.add_argument('-svr_cfg', action='store_true', help='uses local server CFG file')
        args = parser.parse_args(args)
        auth_cfg = args.auth_cfg
        svr_cfg = args.svr_cfg
        if auth_cfg:
            ssh_username, ssh_password, api_key = auth_cfg_import()
        else:
            parser.add_argument('-username', default=None, help='ssh username')
            parser.add_argument('-password', default=None, help='ssh password')
            parser.add_argument('-api_key', default=None, help='API Key, minimum 10 characters')
            ssh_username = args.username
            ssh_password = args.password
            api_key = args.api_key
        if svr_cfg:
            https, interface, port = svr_cfg_import()
        else:
            parser.add_argument('-https', default=True, help='HTTPS, if False, HTTP is used')
            parser.add_argument('-interface', default=False, help='default is Flask will determine')
            parser.add_argument('-port', default=5000, help='default = 5000')
            https = args.https
            interface = args.interface
            port = args.port
        if ssh_username is None:
            print('missing -username from auth_file.txt')
            sys.exit()
        if ssh_password is None:
            print('missing -password from auth_file.txt')
            sys.exit()
        if api_key is None:
            print('missing -api_key from auth_file.txt')
            sys.exit()
        else:
            if len(api_key) < 10:
                print('API Key, minimum 10 characters from auth_file.txt')
                sys.exit()
        if https:
            print('server will use HTTPS')
        else:
            print('server will use HTTP')
    else:
        print('SETUP WIZARD')
        get_username = True
        while get_username:
            ssh_username = input('Enter SSH username: ')
            if len(ssh_username) > 0:
                get_username = False
        get_password = True
        while get_password:
            ssh_password = getpass.getpass('Enter SSH password: ')
            if len(ssh_password) > 0:
                get_password = False
        get_api_key = True
        while get_api_key:
            api_key = input('Enter API key: ')
            if len(api_key) > 2:
                get_api_key = False
            else:
                print('minimum API characters is 10')
        get_https = True
        while get_https:
            https = input('Enable HTTPS? (True/False): ')
            if https == 'False':
                https = False
                get_https = False
            elif https == 'True':
                https = True
                get_https = False
            else:
                print('select either True or False')
        interface = input('Enter API interface (IP): ')
        port = input('Enter API Port Number (5000 is default): ')
    return ssh_username, ssh_password, api_key, https, interface, port


@app.route('/api/<path>', methods=['POST'])
def api_main_route(path):
    if path not in ['ssh_job', 'status', 'stop', 'start']:
        return {'response': 'API path not valid'}, 404, CONTENT
    else:
        auth = request.authorization
        request_dict = request.get_json(silent=True)
        if request_dict.get('api_key') == api_key:
            response, response_code, proceed = authentication_module.login(username=auth.username,
                                                                           password=auth.password)
            if proceed:
                if path == 'ssh_job':
                    response, response_code = process_ssh_job(request_dict.get('job'))
                elif path == 'status':
                    response = {'response': ssh.ssh_threader.status_dict}
                    response_code = 200
                elif path == 'stop':
                    ssh.ssh_threader.disable_ssh_server()
                    timer_expired = False
                    time_now = time.time()
                    while len([x for x in ssh.ssh_threader.status_dict if
                               ssh.ssh_threader.status_dict.get(x)
                               is True]) > 0 or timer_expired is False:
                        time.sleep(1)
                        if int(time.time()) - time_now > 5:
                            timer_expired = True
                    response = {'response': ssh.ssh_threader.status_dict}
                    response_code = 200
                elif path == 'start':
                    if ssh.ssh_threader.ssh_server_active:
                        response = {'response': 'server already active'}
                    else:
                        _ = ssh.ssh_threader.enable_ssh_server()
                        Thread(target=ssh.ssh_threader.start_threaders).start()
                        time.sleep(10)
                        response = {'response': ssh.ssh_threader.status_dict}
                    response_code = 200
        else:
            response = {'response': 'API key does not match'}
            response_code = 401
        return response, response_code, CONTENT


def process_ssh_job(job):
    try:
        session_locked, session_id = ssh.ssh_threader.request_session()
        if session_locked:
            print(session_locked, session_id)
            response = ssh.ssh_threader.run_job(job)
            ssh.ssh_threader.session_clean_up(session_id)
            response_code = 200
        else:
            while ssh.ssh_threader.check_session_status(session_id):
                time.sleep(2)
            else:
                response = ssh.ssh_threader.run_job(job)
                ssh.ssh_threader.session_clean_up(session_id)
                response_code = 200
    except Exception:
        response, response_code = {'response': 'internal server error'}, 500
    return response, response_code


if __name__ == '__main__':
    ssh_username, ssh_password, api_key, https, interface, port = setup(sys.argv[1:])
    ssh.ssh_threader = ssh.SSHThreader(ssh_username, ssh_password)
    Thread(target=ssh.ssh_server).start()
    if https:
        try:
            app.run(port=5000, host=interface, ssl_context=(CERT, KEY))
        except Exception as e:
            print(e)
            sys.exit()
    else:
        try:
            app.run(port=port, host=interface)
        except Exception as e:
            print(e)
            sys.exit()
