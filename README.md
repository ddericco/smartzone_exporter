# SmartZone Exporter

Ruckus SmartZone exporter for https://prometheus.io, written in Python.

This exporter is adapted in part from examples by [Robust Perception](https://www.robustperception.io/writing-a-jenkins-exporter-in-python/) and [Loovoo](https://github.com/lovoo/jenkins_exporter), utilizing the [Ruckus SmartZone API](http://docs.ruckuswireless.com/vscg-carrier/vsz-h-public-api-reference-guide-3-5.html#system-system-summary-get) to query for metrics.

## Background
The goal of this exporter is twofold: provide a faster and more reliable alternative to SNMP for querying metrics from a Ruckus SmartZone controller, while also providing an opportunity to brush up on my (admittedly quite rusty) Python skills. Most of the code will be heavily commented with notes that would be obvious to more experienced developers; perhaps it will be useful for other contributors or developers. There will certainly be additional efficiencies that can be gained, more 'Pythonic' ways of doing certain tasks, or other changes that make this exporter better; contributions are always welcome!

## Features
The following metrics are currently supported:
* Controller summary (uptime, model, serial, hostname, version, AP firmware version)
* System inventory (total APs, discovery APs, connected APs, disconnected APs, rebooting APs, clients)

Additional metrics will be added over time.

## Usage
```
usage: smartzone_exporter.py [-h] -u USER -p PASSWORD -t TARGET [--insecure]
                             [--port PORT]

optional arguments:
  -h, --help            show this help message and exit
  --insecure            Allow insecure SSL connections to Smartzone
  --port PORT           Port on which to expose metrics and web interface
                        (default=9345)

required named arguments:
  -u USER, --user USER  SmartZone API user
  -p PASSWORD, --password PASSWORD
                        SmartZone API password
  -t TARGET, --target TARGET
                        Target URL and port to access SmartZone, e.g.
                        https://smartzone.example.com:8443
```
### Example
```
python smartzone_exporter -u jimmy -p jangles -t https://ruckus.jjangles.com:8443
```

## Requirements
This exporter has been tested on the following versions:

| Model | Version     |
|-------|-------------|
| vSZ-H | 3.5.0.0.808 |

## Installation
```
git clone git@github.com:ddericco/smartzone_exporter.git
cd smartzone_exporter
pip install -r requirements.txt
```
