import sys
import time
from threading import Lock, Thread
from random import randint
from netmiko import SSHDetect, ConnectHandler
import pprint
import os
from pathlib import Path

try:
    local_dir = os.path.dirname(os.path.realpath(__file__))
except Exception:
    local_dir = os.getcwd()

DEVICE_FILE_PATH = str(Path(local_dir, 'device_cfg.txt'))


def netmiko_attr(host, ssh_username, ssh_password, device_type='autodetect'):
    return {
        "device_type": device_type,
        "host": host,
        "username": ssh_username,
        "password": ssh_password,
    }


def _generate_session_id():
    return int(randint(1, 9999))


def append_missing_ssh_thread_to_results(missing_list):
    missing_dict = {}
    for missing_device in missing_list:
        missing_dict[missing_device] = 'No SSH Threader found'
    return missing_dict


class SSHThreader:
    def __init__(self, ssh_username, ssh_password):
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.session_pipeline = []
        self.lock = Lock()
        self.session_locked = False
        self.main_controller_dict = {}
        self.process_job = False
        self.status_dict = {}
        self.read_device_file()
        self.flask_not_ok = False
        if self.cfg_file_found:
            self._create_status_dict()
            print('SSH API Gateway is up, check status to confirm SSH sessions')
        else:
            print('SSH API Gateway is down, failed to load device file')

    def _create_status_dict(self):
        for device in self.device_list:
            self.status_dict[device] = False

    def read_device_file(self):
        try:
            with open(DEVICE_FILE_PATH, 'r') as f:
                self.device_list = list(set([x.replace('\n', '') for x in f.readlines()[1:]]))
                print(self.device_list)
            self.cfg_file_found = True
        except Exception:
            self.device_list = []
            self.cfg_file_found = False
        finally:
            self.ssh_server_active = False

    def request_session(self):
        with self.lock:
            session_id = _generate_session_id()
            self.session_pipeline.append(session_id)
            if self.session_locked is False:
                self.session_locked = True
                return self.session_locked, session_id
            else:
                return False, session_id

    def disable_ssh_server(self):
        self.ssh_server_active = False

    def enable_ssh_server(self):
        if self.ssh_server_active is True:
            return self.cfg_file_found
        else:
            self.ssh_server_active = True
            return self.cfg_file_found

    def check_session_status(self, session_id):
        with self.lock:
            if self.session_locked:
                return self.session_locked
            else:
                if session_id != self.session_pipeline[0]:
                    return True
                else:
                    return False

    def session_clean_up(self, session_id):
        with self.lock:
            self.session_pipeline.remove(session_id)
            self.session_locked = False
            print(f'released session id {session_id}, session_lock is now set to {self.session_locked}')

    def _apply_results_for_off_line_sessions(self):
        """confirms that all ssh sessions are ready and available based on the job keys (devices)
        if a device is False, output and error results are applied since the SSH threader is offline"""
        for device in self.job.keys():
            if self.status_dict.get(device) is False:
                self.job_errors.update({device: 'ssh session not established'})
                self.result_dict = {**self.result_dict, **{device: 'SSH session is not established'}}
            elif self.status_dict.get(device) is None:
                self.job_errors.update({device: 'ssh session not started'})

    def run_job(self, job):
        self.job = job
        wait_for_results = True
        timer_not_exceeded = True
        self.process_job = True
        self.result_dict = {}
        self.job_errors = {}

        job_device_list = list(self.job.keys()).copy()
        start = time.time()
        devices_not_found_in_ssh_threader_list = [x for x in job_device_list if x not in self.device_list]
        if len(devices_not_found_in_ssh_threader_list) > 0:
            self.result_dict = append_missing_ssh_thread_to_results(devices_not_found_in_ssh_threader_list)
            print(devices_not_found_in_ssh_threader_list)
        self._apply_results_for_off_line_sessions()
        while wait_for_results and timer_not_exceeded:
            print(f'Devices which are currently reporting results are {self.result_dict.keys()}')
            print(f'Looking for result output from {job_device_list}')
            if set(self.result_dict.keys()) == set(job_device_list):
                wait_for_results = False
                print(self.result_dict)
                print('all threads accounted for, terminating')
            time.sleep(1)
            if int(time.time() - start) > 15:
                timer_not_exceeded = False
                print('timer exceeded 15 secs')
        self.result_dict.update({'errors': self.job_errors})
        self.process_job = False
        return self.result_dict

    def start_threaders(self):
        for device_id in self.device_list:
            Thread(target=self._ssh_threaders, args=(device_id,)).start()

    def _ssh_threaders(self, device_id):
        ssh_session_ready = False
        while self.ssh_server_active:
            while ssh_session_ready is False:
                print(f'\nstarting ssh session to {device_id}')
                try:
                    guesser = SSHDetect(**netmiko_attr(device_id,
                                                       self.ssh_username,
                                                       self.ssh_password))
                    ssh_session = ConnectHandler(**netmiko_attr(device_id,
                                                                self.ssh_username,
                                                                self.ssh_password,
                                                                guesser.autodetect()))
                    prompt = ssh_session.find_prompt()
                    ssh_session_ready = True
                    print(f'\nSSH session {device_id} now established, now waiting for a job to arrive')
                    with self.lock:
                        self.status_dict.update({device_id: True})
                        print(self.status_dict)
                    ssh_base_timer = int(time.time())
                except Exception as e:
                    print(e)
                    print(f'\nSSH session to {device_id} has failed, trying again in 30 seconds')
                    time.sleep(30)
                    self.status_dict.update({device_id: False})
                    if self.ssh_server_active is False:
                        break
            if self.ssh_server_active is False:
                self.status_dict.update({device_id: False})
                break

            if int(time.time()) - ssh_base_timer > 60:
                try:
                    _ = ssh_session.find_prompt()
                    ssh_base_timer = int(time.time())
                except Exception:
                    ssh_session_ready = False
                    pass

            while self.process_job and ssh_session_ready:
                try:
                    try:
                        _ = ssh_session.find_prompt()
                    except Exception:
                        ssh_session_ready = False
                        pass
                    if ssh_session_ready and self.job.get(device_id) is not None:
                        show_output: dict = {}
                        for command in self.job.get(device_id):
                            print(f'sending {command}')
                            show_output.update({command: ssh_session.send_command(command, expect_string=rf'{prompt}',
                                                                                  cmd_verify=False)})
                        print(f'{device_id} returning success')
                        with self.lock:
                            self.result_dict = {**self.result_dict, **{device_id: show_output}}
                            self.job_errors.update({device_id: 'no error detected'})
                            self.job.pop(device_id)
                        time.sleep(1)
                except Exception:
                    print(f'{device_id} trying to restart')
                    ssh_session_ready = False
            else:
                time.sleep(5)
                try:
                    _ = ssh_session.find_prompt()
                except Exception:
                    print(f'{device_id} trying to restart')
                    ssh_session_ready = False
                    self.status_dict.update({device_id: False})
        else:
            ssh_session.disconnect()
            print(f'ssh disabled for {device_id}')
            self.status_dict.update({device_id: False})


def ssh_server():
    try:
        device_cfg_file_found = ssh_threader.enable_ssh_server()
        if device_cfg_file_found:
            Thread(target=ssh_threader.start_threaders).start()
            print('Threading Status')
            pprint.pprint(ssh_threader.status_dict)
            while True:
                input_value = input('please select either start,status,stop or terminate: ')
                if input_value == 'start':
                    device_cfg_file_found = ssh_threader.enable_ssh_server()
                    service_enabled = ssh_threader.ssh_server_active
                    if service_enabled and device_cfg_file_found:
                        Thread(target=ssh_threader.start_threaders).start()
                        print('Threading Status')
                        pprint.pprint(ssh_threader.status_dict)
                    else:
                        if service_enabled is False:
                            print('service is already enabled, please stop and restart')
                        if device_cfg_file_found is False:
                            print('device CFG is missing or has errors')
                elif input_value == 'stop' or input_value == 'terminate':
                    ssh_threader.disable_ssh_server()
                    pprint.pprint(ssh_threader.status_dict)
                    time_now = int(time.time())
                    timer_expired = False
                    while len([x for x in ssh_threader.status_dict if ssh_threader.status_dict.get(x) is True]) > 0 or \
                            timer_expired:
                        time.sleep(1)
                        print('graceful shutdown in progress, please wait')
                        if int(time.time()) - time_now > 15:
                            timer_expired = True
                    else:
                        print('\ngraceful shutdown has completed\n')
                        if input_value == 'terminate':
                            print('terminating session')
                            sys.exit()
                elif input_value == 'status':
                    pprint.pprint(ssh_threader.status_dict)
                elif input_value == 'clear':
                    os.system('clear')
        else:
            print('ERROR with CFG File')
    except KeyboardInterrupt:
        ssh_threader.disable_ssh_server()
        time_now = int(time.time())
        timer_expired = False
        while len([x for x in ssh_threader.status_dict if ssh_threader.status_dict.get(x) is True]) > 0 or \
                timer_expired:
            time.sleep(1)
            print('graceful shutdown in progress, please wait')
            if int(time.time()) - time_now > 15:
                timer_expired = True
        else:
            sys.exit()
