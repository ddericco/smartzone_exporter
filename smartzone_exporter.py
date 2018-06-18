# requests used to fetch API data
import requests

# Allow for silencing insecure warnings from requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Builtin JSON module for testing - might not need later
import json

# Needed for sleep and exporter start/end time metrics
import time

# argparse module used for providing command-line interface
import argparse

# Prometheus modules for HTTP server & metrics
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY


# Create SmartZoneCollector as a class - in Python3, classes inherit object as a base class
# Only need to specify for compatibility or in Python2

class SmartZoneCollector():

    # Initialize the class and specify required argument with no default value
    # When defining class methods, must explicitly list `self` as first argument

    def __init__(self, target, user, password, insecure):
        # Strip any trailing "/" characters from the provided url
        self._target = target.rstrip("/")
        # Take these arguments as provided, no changes needed
        self._user = user
        self._password = password
        self._insecure = insecure

    def collect(self):

        # Disable insecure request warnings if SSL verification is disabled
        if self._insecure == False:
             requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        # Session object used to keep persistent cookies and connection pooling
        s = requests.Session()

        # Set `verify` variable to enable or disable SSL checking
        # Use string method format methods to create new string with inserted value (in this case, the URL)

        s.get('{}/wsg/api/public/v5_0/session'.format(self._target), verify=self._insecure)

        # Define URL arguments as a dictionary of strings 'payload'
        payload = {'username': self._user, 'password': self._password}

        # Call the payload using the json parameter
        r = s.post('{}/wsg/api/public/v5_0/session'.format(self._target), json=payload, verify=self._insecure)

        # Create a dictionary from the cookie name-value pair, then get the value based on the JSESSIONID key
        session_id = r.cookies.get_dict().get('JSESSIONID')

        # Add HTTP headers for all requests EXCEPT logon API
        # Integrate the session ID into the header
        headers = {'Content-Type': 'application/json;charset=UTF-8', 'Cookie': 'JSESSIONID={}'.format(session_id)}


        # Get SmartZone controller summary

        # Define the metrics we want to capture
        # With the exception of uptime, all of these metrics are strings
        # Following the example of node_exporter, we'll set these string metrics with a default value of 1

        metrics = {
            'model':
                GaugeMetricFamily('smartzone_controller_model', 'SmartZone controller model', labels=["id", "model"]),
            'serialNumber':
                GaugeMetricFamily('smartzone_controller_serial_number', 'SmartZone controller serial number', labels=["id", "serialNumber"]),
            'uptimeInSec':
                CounterMetricFamily('smartzone_controller_uptime_seconds', 'Controller uptime in sections', labels=["id"]),
            'hostName':
                GaugeMetricFamily('smartzone_controller_hostname', 'Controller hostname', labels=["id", "hostName"]),
            'version':
                GaugeMetricFamily('smartzone_controller_version', 'Controller version', labels=["id", "version"]),
            'apVersion':
                GaugeMetricFamily('smartzone_controller_ap_firmware_version', 'Firmware version on controller APs', labels=["id", "apVersion"])
                }

        # Create a list of statuses based on the metrics above (specifically the keys)
        statuses = list(metrics.keys())

        # Get the data from the SmartZone
        # controller = requests.get('{}/api/public/v5_0/controller'.format(self._target), headers=headers, verify=self._insecure)
        controller = requests.get('{}/wsg/api/public/v5_0/controller'.format(self._target), headers=headers, verify=self._insecure)

        # Decode the JSON in the reply from the SmartZone
        result = json.loads(controller.text)

        # When in doubt, review the JSON output _carefully_
        # print(result)

        for c in result['list']:
            id = c['id']
            for s in statuses:
                if s == 'uptimeInSec':
                     metrics[s].add_metric([id], c.get(s))
                # Export a dummy value for string-only metrics
                else:
                     extra = c[s]
                     metrics[s].add_metric([id, extra], 1)

        for m in metrics.values():
            yield m


        # Get SmartZone inventory per zone

        # Define the metrics we want to capture
        # Since the AP and client counts can go up or down, use the gauge metric type
        # Keep the zone name and zone UUID as labels
        metrics = {
            'totalAPs':
                GaugeMetricFamily('smartzone_zone_total_aps', 'Total number of APs in zone', labels=["zone_name","zone_id"]),
            'discoveryAPs':
                GaugeMetricFamily('smartzone_zone_discovery_aps', 'Number of zone APs in discovery state', labels=["zone_name","zone_id"]),
            'connectedAPs':
                GaugeMetricFamily('smartzone_zone_connected_aps', 'Number of connected zone APs', labels=["zone_name","zone_id"]),
            'disconnectedAPs':
                GaugeMetricFamily('smartzone_zone_disconnected_aps', 'Number of disconnected zone APs', labels=["zone_name","zone_id"]),
            'rebootingAPs':
                GaugeMetricFamily('smartzone_zone_rebooting_aps', 'Number of zone APs in rebooting state', labels=["zone_name","zone_id"]),
            'clients':
                GaugeMetricFamily('smartzone_zone_total_connected_clients', 'Total number of connected clients in zone', labels=["zone_name","zone_id"])
                }

        # Define the AP statuses we want to collect as strings in a list - we will loop through this later
        statuses = list(metrics.keys())

        # Get the data from the SmartZone
        # inventory = requests.get('{}/api/public/v5_0/system/inventory'.format(self._target), headers=headers, verify=self._insecure)
        inventory = requests.get('{}/wsg/api/public/v5_0/system/inventory'.format(self._target), headers=headers, verify=self._insecure)

        # Decode the JSON in the reply from the SmartZone
        result = json.loads(inventory.text)

        # When in doubt, review the JSON output _carefully_
        # print result

        # For each zone captured from the query:
        # - Grab the zone name and zone ID for labeling purposes
        # - Loop through the statuses in statuses
        # - For each status, get the value for the status in each zone and add to the metric
        for zone in result['list']:
            zone_name = zone['zoneName']
            zone_id = zone['zoneId']
            for s in statuses:
                metrics[s].add_metric([zone_name, zone_id], zone.get(s))

        # Each metric has several values associated with it, in this case broken down by zone name and zone ID
        for m in metrics.values():
            yield m

        # Get SmartZone AP metrics
        # Use API query instead of simple GET to reduce number of requests and improve performance

        metrics = {
            'alerts':
                GaugeMetricFamily('smartzone_ap_alerts', 'Number of AP alerts', labels=["zone","ap_group","mac","name"]),
            'latency24G':
                GaugeMetricFamily('smartzone_ap_latency_24g_milliseconds', 'AP latency on 2.4G channels in milliseconds', labels=["zone","ap_group","mac","name"]),
            'latency50G':
                GaugeMetricFamily('smartzone_ap_latency_5g_milliseconds', 'AP latency on 5G channels in milliseconds', labels=["zone","ap_group","mac","name"]),
            'numClients24G':
                GaugeMetricFamily('smartzone_ap_connected_clients_24g', 'Number of clients connected to 2.4G channels on this AP', labels=["zone","ap_group","mac","name"]),
            'numClients5G':
                GaugeMetricFamily('smartzone_ap_connected_clients_5g', 'Number of clients connected to 5G channels on this AP', labels=["zone","ap_group","mac","name"]),
            'status':
                GaugeMetricFamily('smartzone_ap_status', 'AP status', labels=["zone","ap_group","mac","name","status"])
                }

        statuses = list(metrics.keys())

        # To-do: set dynamic AP limit based on SmartZone inventory
        raw = {'page': 0, 'start': 0, 'limit': 1000}

        # Grab a list of APs
        aps = requests.post('{}/wsg/api/public/v5_0/query/ap'.format(self._target), json=raw, headers=headers, verify=self._insecure)

        result = json.loads(aps.text)

        # Generate the metrics based on the values
        for ap in result['list']:
            for s in statuses:
                # 'Status' is a string value only, so we can't export the default value
                if s == 'status':
                    state_name = ['Online','Offline','Flagged']
                    # By default set value to 0 and increase to 1 to reflect current state
                    # Similar to how node_exporter handles systemd states
                    for n in state_name:
                        value = 0
                        if ap.get(s) == unicode(n):
                            value = 1
                        metrics[s].add_metric([ap['zoneName'], ap['apGroupName'], ap['apMac'], ap['deviceName'], n], value)
                else:
                    if ap.get(s) is not None:
                        metrics[s].add_metric([ap['zoneName'], ap['apGroupName'], ap['apMac'], ap['deviceName']], ap.get(s))
                    # Return 0 for metrics with values of None
                    else:
                        metrics[s].add_metric([ap['zoneName'], ap['apGroupName'], ap['apMac'], ap['deviceName']], 0)

        # Yield the metrics we want
        for m in metrics.values():
            yield m


# Function to parse command line arguments and pass them to the collector
def parse_args():
    parser = argparse.ArgumentParser(description='Ruckus SmartZone exporter for Prometheus')

    # Use add_argument() method to specify options
    # By default argparse will treat any arguments with flags (- or --) as optional
    # Rather than make these required (considered bad form), we can create another group for required options
    required_named = parser.add_argument_group('required named arguments')
    required_named.add_argument('-u', '--user', help='SmartZone API user', required=True)
    required_named.add_argument('-p', '--password', help='SmartZone API password', required=True)
    required_named.add_argument('-t', '--target', help='Target URL and port to access SmartZone, e.g. https://smartzone.example.com:8443', required=True)

    # Add store_false action to store true/false values, and set a default of True
    parser.add_argument('--insecure', action='store_false', help='Allow insecure SSL connections to Smartzone')

    # Specify integer type for the listening port
    parser.add_argument('--port', type=int, default=9345, help='Port on which to expose metrics and web interface (default=9345)')

    # Now that we've added the arguments, parse them and return the values as output
    return parser.parse_args()

def main():
    try:
        args = parse_args()
        port = int(args.port)
        REGISTRY.register(SmartZoneCollector(args.target, args.user, args.password, args.insecure))
        # Start HTTP server on specified port
        start_http_server(port)
        if args.insecure == False:
             print('WARNING: Connection to {} may not be secure.').format(args.target)
        print("Polling {}. Listening on ::{}".format(args.target, port))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(" Keyboard interrupt, exiting...")
        exit(0)


if __name__ == "__main__":
    main()
