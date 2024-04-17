#!/bin/bash

# Check if the script is executed as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 
    exit 1
fi

# Check if it's running on Ubuntu 18
if [[ $(lsb_release -rs) != "18.04" ]]; then
    echo "This script is intended for Ubuntu 18.04"
    exit 1
fi


# Test Bind9 DNS server
echo "Testing Bind9 DNS server..."
if dig @127.0.0.1 google.com | grep -q "ANSWER SECTION"; then
    echo "Bind9 DNS server installed and configured successfully"
else
    echo "Failed to verify Bind9 DNS server configuration"
    # Add iptables rules to allow traffic on the loopback interface
    iptables -A INPUT -i lo -j ACCEPT
    iptables -A OUTPUT -o lo -j ACCEPT

    # Stop and disable systemd-resolved service
    systemctl stop systemd-resolved.service
    systemctl disable systemd-resolved.service

    # Unlink resolv.conf file
    unlink /etc/resolv.conf

    # Add a temporary nameserver
    echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

    # Install Bind9 DNS server
    apt-get update
    apt-get install -y bind9 bind9utils bind9-doc

    # Configure Bind9
    cat <<EOF > /etc/bind/named.conf.options
acl goodclients {
	127.0.0.1;
	localhost;
	localnets;
};

options {
	directory "/var/cache/bind";
	recursion yes;
	allow-query { goodclients; };
	forwarders {
			1.1.1.1;
			1.0.0.1;
		};

	dnssec-validation auto;
	auth-nxdomain no;
	listen-on-v6 { any; };
    };
EOF

    # Check Bind9 configuration
    if ! named-checkconf; then
        echo "Error in Bind9 configuration"
        exit 1
    fi

    # Restart Bind9 service
    systemctl restart bind9
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    
    # Update package lists
    apt update
    
    # Install necessary packages for adding repositories
    apt install -y apt-transport-https ca-certificates curl software-properties-common
    
    # Fetch Docker repository GPG key and add it to the system's trusted keys
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    
    # Add Docker repository to package sources
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
    
    # Update package lists again
    apt update
    
    # Install Docker CE
    apt install -y docker-ce
    
    echo "Docker installed successfully"
else
    echo "Docker is already installed"
fi


# Function to build Docker image
build_image() {
    # Build Docker image
    docker build -t 3proxy:latest .
}

# Function to import Docker image
import_image() {
    read -p "Enter the path to the Docker image file: " image_path

    # Import Docker image
    docker load -i "$image_path"
}

# Prompt user for building or importing Docker image
echo "Choose an option:"
echo "1. Build Docker image"
echo "2. Import existing Docker image"

read -p "Enter your choice (1 or 2): " choice

case $choice in
    1)
        build_image
        ;;
    2)
        import_image
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Function to check and create directories if they don't exist
check_and_create_directories() {
    if [ ! -d "./config" ]; then
        mkdir ./config
        echo "Created directory ./config"
    fi

    if [ ! -d "./log" ]; then
        mkdir ./log
        echo "Created directory ./log"
    fi
}

# Function to stop and remove 3proxy container if it's already running
stop_and_remove_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^3proxy$"; then
        docker stop 3proxy
        docker rm 3proxy
        echo "Stopped and removed existing 3proxy container"
    fi
}
check_and_create_directories
stop_and_remove_container

# Run the container named 3proxy
docker run -d \
    --name 3proxy \
    --restart always \
    --net host \
    --cap-add NET_ADMIN \
    -v ./config:/app/config \
    -v ./log:/app/log \
    3proxy:latest

echo "Printing container logs:"
sleep 3 
docker logs 3proxy

