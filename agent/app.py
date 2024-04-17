from flask import Flask, request, jsonify
import random
import subprocess
import psutil
from datetime import datetime
import re
import concurrent.futures
import requests
import logging
import sys 
from bs4 import BeautifulSoup
import os
import uuid
import json

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logging level to capture all events

# Create a file handler to log to a file
file_handler = logging.FileHandler('3proxy_api.log')
file_handler.setLevel(logging.DEBUG)  # Set the file handler's logging level

# Create a console handler to log to the terminal
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # Set the console handler's logging level

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = Flask(__name__)

# Define the global variable for the 3proxy configuration file location
config_file_path = "/app/config/3proxy.cfg"
CONFIG_PATH = '/app/config/'
SECRET_FILE = '/app/config/secret'
credentials_file_path = "/app/config/creds/"

# Define a class to represent a proxy configuration
class Proxy:
    def __init__(self):
        self.port = None
        self.protocol = "ipv4"
        self.external_address = None

def authenticate(secret):
    try:
        with open(SECRET_FILE, 'r') as secret_file:
            # Read the password from the secret file
            stored_secret = secret_file.read().strip()
            # Compare the provided password with the stored password
            if secret == stored_secret:
                return True  # Authentication successful

    except FileNotFoundError:
        # Handle the case where the user file is not found
        print("User file not found.")
    except Exception as e:
        # Handle other exceptions (e.g., file read error)
        print(f"Error: {str(e)}")

    return False  # Authentication failed

def reload_3proxy_service():
    logger = logging.getLogger(__name__)
    try:
        # Read the PID from the PID file
        with open("/app/3proxy/3proxy.pid", "r") as pid_file:
            pid = pid_file.read().strip()

        # Execute the command to send USR1 signal to 3proxy
        subprocess.call(["/bin/kill", "-USR1", pid])

        logger.info("3proxy service reloaded successfully.")
        return True
    except FileNotFoundError:
        # Handle the case where the PID file is not found
        logger.error("Error: PID file not found.")
        return False
    except Exception as e:
        # Catch any other unexpected errors and log the error message
        logger.error(f"Unexpected error: {e}")
        return False
        
# Function to generate /24 subnet IPs, subnet is in form X.X.X 
# Generated IPs are from X.X.X.1 -> X.X.X.254 
def generate_ips(subnet):
    return [f"{subnet}.{i}" for i in range(1, 255)]

# Define regular expression patterns for matching proxy configurations and options
proxy_pattern = re.compile(r'^\s*proxy\s+(-[a-zA-Z0-9]+(?:\s+[^\s#]+)*)')

# Define a function to parse proxy configurations with error handling
def parse_proxy_configurations(config_file_path):
    proxy_configs = []

    def process_config_file(file_path):
        try:
            with open(file_path, 'r') as config_file:
                current_proxy_config = None
                for line in config_file:
                    match_proxy = proxy_pattern.match(line)
                    if match_proxy:
                        current_proxy_config = Proxy()
                        proxy_configs.append(current_proxy_config)
                        options = match_proxy.group(1).split() if match_proxy.group(1) else []
                        for option in options:
                            if option.startswith('-p'):
                                current_proxy_config.port = int(option[2:])
                            elif option == '-6':
                                current_proxy_config.protocol = "ipv6"
                            elif option.startswith('-e'):
                                current_proxy_config.external_address = option[2:]

                    # Check for 'include' stanzas and parse included files
                    if line.startswith('include '):
                        included_file = line.split('include ')[1].strip()
                        included_file_path = os.path.join(os.path.dirname(file_path), included_file)
                        process_config_file(included_file_path)
        except Exception as e:
            # Ignore errors for included files
            pass

    try:
        process_config_file(config_file_path)
    except FileNotFoundError:
        return None, "Configuration file not found"
    except Exception as e:
        return None, str(e)
    return proxy_configs, None


def add_proxy(port,protocol,external):
    # Parse incoming request
    incoming_port = port
    incoming_address = "0.0.0.0"
    outgoing_protocol = protocol
    outgoing_ip = external

    # Use parse_proxy_configurations function to get a list of configured proxies
    parsed_configs, error_message = parse_proxy_configurations(config_file_path)
    
    if error_message:
        return jsonify({"error": error_message})

    # Check if the port is already configured
    for proxy_config in parsed_configs:
        if proxy_config.port == port:
            return jsonify({"error": f"Port {port} is already configured. Choose a different port number."})

    # Create a new config file named <port number>.cfg
    new_config_file_path = os.path.join(CONFIG_PATH, f"{incoming_port}.cfg")

    # Add the file in the main 3proxy configuration file using "include <file-path>"
    with open(config_file_path, 'a') as main_config_file:
        main_config_file.write(f"include {new_config_file_path}\n")

    # Create the contents of <port number>.cfg
    with open(new_config_file_path, 'w') as new_config_file:
        new_file_content = f"""flush
auth strong
deny *
proxy -p{incoming_port} {'-6 ' if outgoing_protocol == 'ipv6' else ''}-a -n -i{incoming_address} {'-e' if outgoing_ip else ''}{outgoing_ip}\n"""
        new_config_file.write(new_file_content)


@app.route('/install4.json', methods=['POST'])
def install4():

    secret = request.json.get("secret")
    if not secret:
        return jsonify({"error": "Authentication required"}), 401
    
    if not authenticate(secret):
        return jsonify({"error": "Authentication failed"}), 401

    # 254 port numbers 
    port_start = 3131
    
    # TODO : Add validations for subnet 
    subnet = request.json.get("subnet")
    ip_addresses = generate_ips(subnet)
    
    
    status_list = []
    errors = []
    
    for ip_address in ip_addresses:
        port = port_start
        protocol = "ipv4"
        external = ip_address
        
        # Call add_proxy function for each IP address
        status = add_proxy(port, protocol, external)
        
        # Append status to status_list
        status_list.append(status)
        
        # If status is not None (indicating an error occurred), append the error message to errors list
        if status is not None:
            errors.append(status)
        
        # Increment port for the next iteration
        port += 1
    
    # Check if all proxies were added successfully
    if all(status is None for status in status_list):
        reload_3proxy_service()
        return jsonify({'status': 'success'})
    else:
        # Return status and errors encountered during proxy additions
        return jsonify({'status': 'failure', 'errors': errors})
    
def random_ipv6_address(subnet):
    #Extract the subnet segments from the provided /48 IPv6 subnet
    subnet_segments = subnet.split(':')[:3]  # Extracting the first three segments
        
    # Generate five random hexadecimal segments
    random_segments = [f"{random.randint(0, 65535):04x}" for _ in range(5)]
    return ":".join(subnet_segments + random_segments)
    
@app.route('/install6.json', methods=['POST'])
def install6():
    
    secret = request.json.get("secret")
    if not secret:
        return jsonify({"error": "Authentication required"}), 401
    
    if not authenticate(secret):
        return jsonify({"error": "Authentication failed"}), 401

    port_from = request.json.get("port_from")
    port_to = request.json.get("port_to")
    subnet = request.json.get("subnet")
    external = request.json.get("external")  # Check if the request includes external parameter
    
    if not external:
        # Combine subnet segments with random segments to form complete IPv6 addresses
        ipv6_addresses = [random_ipv6_address(subnet) for _ in range(port_from, port_to + 1)]
    else:
        ipv6_addresses = external
    
    status_list = []
    errors = []

    for index, ipv6_address in enumerate(ipv6_addresses, start=port_from):
        port = index
        protocol = "ipv6"
        
        # Call add_proxy function for each IPv6 address
        status = add_proxy(port, protocol, ipv6_address)
        
        # Append status to status_list
        status_list.append(status)
        
        # If status is not None (indicating an error occurred), append the error message to errors list
        if status is not None:
            errors.append(status)
    
    # Check if all proxies were added successfully
    if all(status is None for status in status_list):
        reload_3proxy_service()
        return jsonify({'status': 'success'})
    else:
        # Return status and errors encountered during proxy additions
        return jsonify({'status': 'failure', 'errors': errors})

@app.route('/get6.json', methods=['GET'])
def get6():

    password = request.json.get("password")
    if not password:
        return jsonify({"error": "Authentication required"}), 401
    
    if not authenticate(password):
        return jsonify({"error": "Authentication failed"}), 401
        
    try:
        # Use parse_proxy_configurations function to get a list of configured proxies
        parsed_configs, error_message = parse_proxy_configurations(config_file_path)
        
        if error_message:
            return jsonify({'status': 'error', 'message': error_message})
        
        # Initialize a dictionary to store IPv6 proxies
        ipv6_proxies = {}
        
        # Iterate over the parsed configurations to find IPv6 proxies
        for proxy_config in parsed_configs:
            if proxy_config.protocol == "ipv6" and proxy_config.port:
                # Add the IPv6 proxy to the dictionary
                ipv6_proxies[str(proxy_config.port)] = proxy_config.external_address
        
        # Return success along with the IPv6 proxies
        return jsonify({'status': 'success', 'IPs': ipv6_proxies})
    
    except Exception as e:
        # Log the error
        logger.error(f"Error in /get6.json: {e}")
        
        # Return error response
        return jsonify({'status': 'error', 'message': str(e)})

def update_acl(port):
    try:
        # Check if the configuration file for the given port exists
        config_file = os.path.join(CONFIG_PATH, f"{port}.cfg")
        if os.path.exists(config_file):
            with open(config_file, 'r') as cfg_file:
                lines = cfg_file.readlines()
                proxy_line = ""
            # Find the line starting with 'proxy '
            for i, line in enumerate(lines):
                if line.strip().startswith('proxy '):
                    proxy_line = line
                    break
            # Iterate over all the files in the credentials_file_path
            port_found = False
            lines = []
            for filename in os.listdir(credentials_file_path):
                filepath = os.path.join(credentials_file_path, filename)
                # Load content of the credentials file
                with open(filepath, 'r') as f:
                    credentials_data = json.load(f)
                # Extract port range from credentials data
                port_from = credentials_data.get("port_from")
                port_to = credentials_data.get("port_to")
                # Check if the port falls within the range
                if port_from <= port <= port_to:
                    port_found = True
                    # Update the port.cfg file
                    lines.append("flush \n")
                    lines.append(f'auth {credentials_data["authtype"]}\n')
                    if credentials_data["authtype"] == "strong":
                        # Add line users username:CL:password after 'auth' line
                        lines.append(f'users {credentials_data["username"]}:CL:{credentials_data["password"]}\n')
                    
                    if credentials_data["authtype"] == "strong":
                        # Add 'allow' for user line at the end of the file
                        lines.append(f'allow {credentials_data["username"]}\n')
                    else:
                        # Add 'allow' for IP line at the end of the file
                        lines.append(f'allow * {credentials_data["ip"]}\n')
                    
                    lines.append(proxy_line)
                    break
            if not port_found:
                lines.append('flush \n')
                lines.append(f'auth strong\n')
                lines.append(f'deny *\n')
                lines.append(proxy_line)
            # Write the updated lines back to the file
            with open(config_file, 'w') as cfg_file:
                cfg_file.writelines(lines)
            logger.info(f"ACL updated for port {port}.")
            return jsonify({'status': 'success', 'message': f'ACL updated for port {port}.'})
        else:
            return jsonify({'status': 'error', 'message': f'Configuration file not found for port {port}.'})
    except Exception as e:
        # Log the error
        logger.error(f"Error in updating ACL for port {port}: {e}")
        # Return error response
        return jsonify({'status': 'error', 'message': str(e)})

    
@app.route('/create_user_credentials.json', methods=['POST'])
def create_user_credentials():
    secret = request.json.get("secret")
    if not secret:
        return jsonify({"error": "Authentication required"}), 401
    
    if not authenticate(secret):
        return jsonify({"error": "Authentication failed"}), 401

    try:
        port_from = request.json.get("port_from")
        port_to = request.json.get("port_to")
        username = request.json.get("username")
        password = request.json.get("password")

        # Generate a UUID for the filename
        filename = str(uuid.uuid4()) 
        
        # Create the full path for the credentials file
        filepath = os.path.join(credentials_file_path, filename + ".json" )
        
        # Create a dictionary with the received data
        credentials_data = {
            "port_from": port_from,
            "port_to": port_to,
            "username": username,
            "password": password,
            "authtype": "strong"
        }
        
        # Write the data to a JSON file
        with open(filepath, 'w') as f:
            json.dump(credentials_data, f)
        
        # Iterate through ports and create credentials
        for port in range(port_from, port_to + 1):
            update_acl(port)

        reload_3proxy_service()
        # Return success response
        return jsonify({'status': 'success', 'credential_id': filename})

    except Exception as e:
        # Log the error
        logger.error(f"Error in /create_user_credentials.json: {e}")
        
        # Return error response
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/create_ip_credentials.json', methods=['POST'])
def create_ip_credentials():
    secret = request.json.get("secret")
    if not secret:
        return jsonify({"error": "Authentication required"}), 401
    
    if not authenticate(secret):
        return jsonify({"error": "Authentication failed"}), 401

    try:
        port_from = request.json.get("port_from")
        port_to = request.json.get("port_to")
        ip = request.json.get("ip")

        # Generate a UUID for the filename
        filename = str(uuid.uuid4()) 
        
        # Create the full path for the credentials file
        filepath = os.path.join(credentials_file_path, filename + ".json" )
        
        # Create a dictionary with the received data
        credentials_data = {
            "port_from": port_from,
            "port_to": port_to,
            "ip": ip,
            "authtype": "iponly"
        }
        
        # Write the data to a JSON file
        with open(filepath, 'w') as f:
            json.dump(credentials_data, f)
        
        # Iterate through ports and create credentials
        for port in range(port_from, port_to + 1):
            update_acl(port)
        reload_3proxy_service()
        # Return success response
        return jsonify({'status': 'success', 'credential_id': filename})

    except Exception as e:
        # Log the error
        logger.error(f"Error in /create_ip_credentials.json: {e}")
        
        # Return error response
        return jsonify({'status': 'error', 'message': str(e)})
    
@app.route('/delete_credentials.json', methods=['POST'])
def delete_credentials():
    secret = request.json.get("secret")
    if not secret:
        return jsonify({"error": "Authentication required"}), 401
    
    if not authenticate(secret):
        return jsonify({"error": "Authentication failed"}), 401

        
    try:
        credential_id = request.json.get("id")
        filepath = os.path.join(credentials_file_path, f"{credential_id}.json")
        
        # Check if the credentials file exists
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                credentials_data = json.load(f)
            
            # Delete the credentials file
            os.remove(filepath)
            
            # Iterate over the range of ports specified in the credentials and update ACLs
            for port in range(credentials_data["port_from"], credentials_data["port_to"] + 1):
                update_acl(port)
            reload_3proxy_service()
            # Return success response
            return jsonify({'status': 'success', 'message': f'Credentials with ID {credential_id} deleted successfully.'})
        else:
            return jsonify({'status': 'error', 'message': f'Credentials with ID {credential_id} not found.'})
    except Exception as e:
        # Log the error
        logger.error(f"Error in /delete_credentials.json: {e}")
        
        # Return error response
        return jsonify({'status': 'error', 'message': str(e)})

    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3120, debug=True)
