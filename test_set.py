import requests
import json
from requests.auth import HTTPBasicAuth
import urllib3
import pprint
import concurrent.futures
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = 'http://127.0.0.1:5000/'
ssh_api_gw = 'api/ssh_job'
status = 'api/status'
start = 'api/start'
stop = 'api/stop'

USERNAME = 'admin'
PASSWORD = 'cisco_gw'

api_key =  '1234567890'

job = {'api_key': api_key,
       'job': {
           '192.168.0.221': ['show ip route', 'show ip arp', 'show version', 'show running'],
           '192.168.0.222': ['show ip route', 'show ip arp', 'show version', 'show running'],
           '192.168.0.223': ['show ip route', 'show ip arp', 'show version', 'show running'],
           '192.168.0.224': ['show ip route', 'show ip arp', 'show version', 'show running'],
           '192.168.0.225': ['show ip route', 'show ip arp', 'show version', 'show running'],
           '192.168.0.226': ['show ip route', 'show ip arp', 'show version', 'show running'],
       }}


concurrent_sessions = list(range(0, 5))
compeleted_sessions = concurrent_sessions.copy()

def ssh_post(job, session_id):
    pprint.pprint(
        requests.post(BASE_URL + ssh_api_gw, data=json.dumps(job), auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=False,
                      headers={"Content-Type": "application/json"}).json())
    return session_id

def start_test_job():
    start_time = int(time.time())
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(concurrent_sessions)) as executor:
        future_ssh = {executor.submit(ssh_post, job, session_id): session_id for session_id in concurrent_sessions}
        for future_id in concurrent.futures.as_completed(future_ssh):
            session_id= future_id.result()
            print(f'session {session_id} completed')
            try:
                compeleted_sessions.remove(session_id)
            except Exception:
                print('duplicate session ID...')
            print(f'timer is {int(time.time()-start_time)} seconds')
    if len(compeleted_sessions) > 0:
        print('hmmm, we have missing data')
    else:
        print(f'all sessions accounted for')
    print(f'job/s took {int(time.time()-start_time)} seconds to complete')

def call_status():
    pprint.pprint(requests.post(BASE_URL + status, data =json.dumps({'api_key': api_key}),
                            auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=False,
                            headers={"Content-Type": "application/json"}).json())


def call_stop():
    pprint.pprint(requests.post(BASE_URL + stop, data =json.dumps({'api_key': api_key}),
                                auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=False,
                                 headers={"Content-Type": "application/json"}).json())


def call_start():
    pprint.pprint(requests.post(BASE_URL + start, data =json.dumps({'api_key': api_key}),
                                auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=False,
                                headers={"Content-Type": "application/json"}).json())

if __name__ == '__main__':
    call_status()
    start_test_job()
