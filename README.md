<h1><strong><center> API SSH Gateway</center> </strong></h1>

The API SSH gateway was primarily written to work with Cisco networking devices. As most networking devices don’t have API interfaces, access is mainly restricted to SSH or overly complex Netconf which uses YANG. 

The CLI holds a wealth of information but getting access to this information (quickly and at scale) can be a challenge. Once the SSH API server is online (SSH sessions are established), an API call is sent to the API interface which relays an incoming request (embedded within the JSON) into a queuing agent. The queuing agent is responsible for queuing and responding to each API request. 

Having all SSH sessions permanently connected has its advantages. The most noteworthy is no setup lag. This reduces the delay from receiving the API call, setting up each SSH session and then responding. As there is only one established SSH session (per device), only one API call can be processed at any time. If multiple requests are received, they are processed in a first come, first serve basis.

The API SSH gateway is built using threading. Once SSH sessions are established, they remain active. If a SSH session drops or is disconnected, the API SSH gateway will try and reestablish it. To stop the SSH sessions from going stale, every 5 seconds, the server will press enter on the remote device. If an API request arrives for a device which is not established then the result will say “SSH session not established’. For example, if 2 out of 50 devices are offline, the offline devices are skipped, results will be seen from the other 48 and an error for the skipped two. 

For simplicity, I’ve created a tool which parses YAML. An example of the YAML structure is found in the repo (named test.yaml). The fetch.py file is responsible for parsing the YAML file, creating the JSON, sending the API, receiving the results and writing the results to the output folder. 

<center><h3 style="color: green"> Folder Structure</h3></center>

•	Code /<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; main.py: the front end python code (flask and args).<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; authentication_module.py: location of the API username and password. <br> 
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;Could you expanded to use LDAP or some other authentication method.<br> 
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; ssh.py: location of the SSH (threaders) and queuing agent<br> 
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; remote_management.py: check status, start or stop the SSH service. <br>
•	setup_cfg/<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; device_cfg.txt: a list of your SSH devices (either IP or Name)<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; auth_file.txt (optional): stores the SSH username, password and server API key (or use input arguments)<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; server_cfg.txt, server related configuration (http/https, API IP Address and port)<br>
•	certs /<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; server.cert: cert for testing<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; server.key: key for testing<br>

•	client/
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; fetch.py: Used to fetch the show commands, must include the YAML file name<br>
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; exmample yaml file


<center><h3 style="color: green"> Environment setup (Linux and Mac)</h3></center>

Start by creating an new directory called projects (or any other name)

mkdir projects<br>
cd projects

Then clone the git repository
https://github.com/atxit/ssh_api_gateway.git

Next, cd ssh_api_gateway and create a python venv

python3 -m venv env<br> 
source env/bin/activate<br> 
pip3 install --upgrade pip<br> 
pip3 install -r requirements.txt<br> 


<center><b>API Username and Password</b></center>

I have added a file called authentication_module.py which is imported during startup. This file contains a static username and password however, this could easily be integrated into LDAP (and should be) if used in a production network. 

<b><center>Server setup</center></b>

The server can be setup using three different methods:

1)	Using the setup wizard. No information is saved
2)	Using the auth_file.txt and server_cfg.txt files
3)	entered authentication arguments. 

Note: configuration options found in the server_cfg.txt file can not be passed as arguments
They must be provided using the wizard or directly from the file. 

Arguments

  -h, --help          		show this help message and exit<br>
  -auth_cfg           		uses local cred file<br>
  -username USERNAME  	ssh username<br>
  -password PASSWORD 	ssh password<br>
  -api_key API_KEY    	API Key, minimum 10 characters<br>
  -wizard             		enter setup wizard mode

When -auth_cfg flag is entered, the auth_cfg.txt file is used.<br>
If no flag is seen then the wizard starts.<br>
or -auth_cfg flag is flagged then -username, -password and -api_key must be provided.

Example: Starting the server using arguments
<i>python3 ssh_api.py -username admin -password cisco -api_key 5544332233444</i>

Example: Starting the server using the auth_file
<i>python3 main.py -auth_cfg</i>

Example: Starting the server using the wizard
<i>python3 main.py</i>
<br>
SETUP WIZARD<br>
Enter SSH username: admin<br>
Enter SSH password: <br>
Enter API key: 5544332233444<br>
Enable HTTPS? (True/False): True<br>
Enter API interface (IP): 127.0.0.1<br>
Enter API Port Number (5000 is default): <br>
['192.168.0.221', '192.168.0.222', '192.168.0.223']<br>
SSH API Gateway is up, check status to confirm SSH sessions<br>
Threading Status<br>

 * Serving Flask app 'main' (lazy loading)

please select either start,status,stop or terminate: 
starting ssh session to 192.168.0.223
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on https://127.0.0.1:5000/ (Press CTRL+C to quit)

please select either start,status,stop or terminate: 
SSH session 192.168.0.221 now established, now waiting for a job to arrive<br>
{'192.168.0.221': True, '192.168.0.222': False, '192.168.0.223': False}

please select either start,status,stop or terminate: <br>
SSH session 192.168.0.222 now established, now waiting for a job to arrive
{'192.168.0.221': True, '192.168.0.222': True, '192.168.0.223': False}

SSH session 192.168.0.223 now established, now waiting for a job to arrive
{'192.168.0.221': True, '192.168.0.222': True, '192.168.0.223': True}

please select either start,status,stop or terminate: 

As the server begins setting up SSH sessions, onscreen updates will be provided.
True states that the SSH session has been established, False is an non-established SSH session.

From the console, there are four control options

please select either start,status,stop or terminate:

•	<b>Start</b>: this happens automatically during setup<br><br>
<i>please select either start,status,stop or terminate: start
Threading Status
{'192.168.0.221': False, '192.168.0.222': False, '192.168.0.223': False}
starting ssh session to 192.168.0.222p
lease select either start,status,stop or terminate: 
starting ssh session to 192.168.0.223
starting ssh session to 192.168.0.221
</i>

SSH session 192.168.0.221 now established, now waiting for a job to arrive<br>

•	<b>Stop</b>: Graceful shutdown of all SSH sessions<br>
•	<b>Terminate</b>: Graceful shutdown of all SSH session then terminates the server<br>
<i><br>
please select either start,status,stop or terminate: terminate<br>
{'192.168.0.221': True, '192.168.0.222': True, '192.168.0.223': True}<br>
graceful shutdown in progress, please wait<br>
graceful shutdown in progress, please wait<br>
graceful shutdown in progress, please wait<br>
graceful shutdown in progress, please wait<br>
graceful shutdown in progress, please wait<br>
ssh disabled for 192.168.0.221<br>
graceful shutdown in progress, please wait<br>
ssh disabled for 192.168.0.222<br>
<br>ssh disabled for 192.168.0.223
graceful shutdown in progress, please wait<br>
</i>

•	Status: request SSH status<br>
<i>
please select either start,status,stop or terminate: status
{'192.168.0.221': True, '192.168.0.222': True, '192.168.0.223': True}</i>
All actions (except terminate) are available when using remote_management.py

<i>
python3 remote_management.py -status<br>
{'response': {'192.168.0.221': False,
              '192.168.0.222': False,
              '192.168.0.223': False}}


python3 remote_management.py -start<br>
{'response': {'192.168.0.221': True,
              '192.168.0.222': True,
              '192.168.0.223': True}}


python3 remote_management.py -stop<br>
{'response': {'192.168.0.221': False,
              '192.168.0.222': False,
              '192.168.0.223': False}}
</i><br>

<h2><center>Fetching show commands</center></h2>
Now that the server is up and working and our SSH sessions are established, it's time to pull some data. <br><br>
<i>
Before starting, configure the yaml file

<img src=images/yaml_example.png>
</i>

Note, output folder is where the results are saved<br>
if the path starts with a / then this is considered a full path
if the path doesn't start with a /, example, test/file then current folder is used as the base dir


python3 fetch.py test.yaml or python3 fetch.py test #either is acceptable.<br>

Errors are displayed

ERROR 192.168.0.220: No SSH Threader found<br>
ERROR 192.168.0.224: No SSH Threader found<br>
</i>
Both 192.168.0.220 and .224 are configured in the YAML however, neither are online. 

<img src="images/output%20results.png">



 


  










