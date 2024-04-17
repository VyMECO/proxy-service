# proxy
Easy installation of a proxy service + configuration management via API.

## Overview 

The goal of this project is to create the following things: 

1. Docker image which runs 3proxy service and an API to control 3proxy service 
2. API to provide functionalities to configure IPv4 and IPv6 proxies. Further it provides functionality to add/delete credenetials for individual proxies. 
3. Installer script to install docker, bind9 server for local DNS functionality, build the docker image, and start the container 
		
## 1. install_env.sh 
	
 This is the installer script, currently it supports Ubuntu 18.04 only, to add further distros it needs to be tested on those distros. 
	Usuage: 
		bash install_env.sh 
		
		steps:
			i. checks if script is executed as root (required)
			ii. checks if target system is 18.04 (only supported right now)
			iii. checks if local DNS server running, if not install bind9 
			iv. check is docker is installed, if not install docker 
			v. prompt user if they want to build 3proxy image, or to use existing image (ask for image path)
			vi. starts container 
			
## 2. helper/init.sh 

 Executed on container start, checks if 3proxy.cfg exist already, if not then copy a stable version 
	Generate secret password 
	Start supervisor services for 3proxy and API 
	
## 3. 3proxy container: 
	
 container utilizes host network and NET_ADMIN capabilities (to add IPv6 address to interfaces)
	mounts config directory to /app/config in container 
	echo port's configuration is written to it's own file, like for port 4000, /app/config/4000.cfg (inside container path) is created 
	mounts log directory to /app/log/
	secret file path config/secret (/app/config/secret inside container)

## 4. API details : 

	API provides following endpoints: (all endpoints require secret)
	
	i. /install4.json
	ii. /install6.json
	iii. /get6.json
	iv. /create_user_credentials.json
	v. /create_ip_credentials.json
	vi. /delete_credentials.json
	
## 5. Exporting/Saving image and reusing 

 To export 3proxy image, run this command where the image is already present/built 
	
 	docker save -o 3proxy.tar 3proxy:latest

Load on target machine:

	docker load -i 3proxy.tar
	
	Also in the install_env.sh it provides the user option to load an existing image. 
