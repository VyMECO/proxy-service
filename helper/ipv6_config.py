#!/usr/bin/env python3
import subprocess
import logging
import os

# Configure the logging settings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log to the terminal
    ]
)

def parse_ipv6_from_config(config_file):
    ipv6_addresses = []
    processed_files = set()

    def process_file(file_path):
        with open(file_path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'proxy -p' in line:
                    parts = line.split('-e')
                    if len(parts) > 1:
                        ipv6_addresses.append(parts[1].strip())

                # Check for 'include' stanzas and parse included files
                if line.startswith('include '):
                    included_file = line.split('include ')[1].strip()
                    included_file_path = os.path.join(os.path.dirname(file_path), included_file)
                    if included_file_path not in processed_files:
                        processed_files.add(included_file_path)
                        process_file(included_file_path)

    process_file(config_file)

    return ipv6_addresses

def get_primary_interface():
    try:
        # Run ip route get to find the primary interface
        output = subprocess.check_output(['ip', 'route', 'get', '8.8.8.8'], stderr=subprocess.STDOUT, universal_newlines=True)
        lines = output.strip().split('\n')
        for line in lines:
            if 'dev' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'dev' and i + 1 < len(parts):
                        return parts[i + 1]

    except subprocess.CalledProcessError:
        pass

    # If no primary interface is found, return a default value (e.g., 'eth0')
    return 'eth0'

def check_and_assign_ipv6(ipv6_addresses, interface):
    configured_addresses = 0 
    for ipv6 in ipv6_addresses:
        try:
            # Split the 'ip' and 'grep' commands, and use subprocess.PIPE for piping
            command1 = ['ip', '-6', 'address', 'show', 'dev', interface]
            command2 = ['grep', '-q', ipv6]

            process1 = subprocess.Popen(command1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process2 = subprocess.Popen(command2, stdin=process1.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process1.stdout.close()  # Close the stdout of process1 so that process2 receives EOF

            # Wait for the second process to finish and get its return code
            return_code = process2.wait()

            if return_code != 0:
                logging.info(f"Adding IPv6 address: {ipv6} to {interface}")
                subprocess.call(['ip', '-6', 'address', 'add', ipv6, 'dev', interface])
                configured_addresses += 1

        except subprocess.CalledProcessError as e:
            logging.error(f"Error checking/adding IPv6 address: {ipv6} - {str(e)}")
    return configured_addresses

if __name__ == "__main__":
    config_file = '/app/config/3proxy.cfg'
    ipv6_addresses = parse_ipv6_from_config(config_file)
    primary_interface = get_primary_interface()
    
    logging.info(f"Extracted Primary Interface: {primary_interface}")
    # Logging information about the IPv6 addresses
    total_ipv6_addresses = len(ipv6_addresses)

    configured_addresses = check_and_assign_ipv6(ipv6_addresses, primary_interface)
    
    logging.info(f"Total IPv6 addresses: {total_ipv6_addresses}")
    logging.info(f"Already configured: {total_ipv6_addresses - configured_addresses}")
    logging.info(f"Configured in this script: {configured_addresses}")

