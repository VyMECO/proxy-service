# proxy
Easy installation of a proxy service + configuration management via API.

## Overview 

The goal of this project is to create the following things: 

1. Docker image which runs 3proxy service and an API to control 3proxy service 
2. API to provide functionalities to configure IPv4 and IPv6 proxies. Further it provides functionality to add/delete credenetials for individual proxies. 
3. Installer script to install docker, bind9 server for local DNS functionality, build the docker image, and start the container 
		
## 1. install_env.sh 
	
This is the installer script, currently it supports Ubuntu 18.04 only, to add further distros it needs to be tested on those distros. 

```bash
bash install_env.sh 
```

Steps performed by `install_env.sh`:

1. checks if script is executed as root (required)
2. checks if target system is 18.04 (only supported right now)
3. checks if local DNS server running, if not install bind9 
4. check is docker is installed, if not install docker 
5. prompt user if they want to build 3proxy image, or to use existing image (ask for image path)
6. starts container 
			
## 2. helper/init.sh 

1. Executed on container start, checks if 3proxy.cfg exist already, if not then copy a stable version 
2. Generate secret password 
3. Start supervisor services for 3proxy and API 
	
## 3. 3proxy container: 
	
1. container utilizes host network and NET_ADMIN capabilities (to add IPv6 address to interfaces)
2. mounts config directory to /app/config in container 
3. echo port's configuration is written to it's own file, like for port 4000, /app/config/4000.cfg (inside container path) is created 
4. mounts log directory to /app/log/
5. secret file path config/secret (/app/config/secret inside container)

## 4. API details : 

API provides following endpoints: (API is running at port 3120, and all endpoints require 'secret' parameter passed to them)
	
1. /install4.json
2. /install6.json
3. /get6.json
4. /create_user_credentials.json
5. /create_ip_credentials.json
7. /delete_credentials.json
	
## 5. Exporting/Saving image and reusing 

To export 3proxy image, run this command where the image is already present/built 
	
```bash
docker save -o 3proxy.tar 3proxy:latest
```

Load on target machine:

```bash
docker load -i 3proxy.tar
```

Also in the install_env.sh it provides the user option to load an existing image. 
