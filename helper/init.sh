#!/bin/bash

# Step 1: Check if /app/config/3proxy.cfg exists, if not, copy from /app/static/3proxy.cfg
if [ ! -f "/app/config/3proxy.cfg" ]; then
    cp /app/helper/3proxy.cfg /app/config/3proxy.cfg
fi

if [ ! -f "/app/config/3130.cfg" ]; then
    cp /app/helper/3130.cfg /app/config/3130.cfg
fi

# Step 2: Create directory /app/config/creds/ if not exists
mkdir -p /app/config/creds/

# Step 3: Create file /app/config/secret if not exists and add a random generated alpha numeric password
if [ ! -f "/app/config/secret" ]; then
    pw=$(openssl rand -base64 12)
    echo "$pw" > /app/config/secret
fi

# Step 4: Echo the password
echo "SECRET: $(cat /app/config/secret)"
echo "Starting supervisor services"
# Step 5: Run supervisord
/usr/bin/supervisord -c /etc/supervisor/supervisord.conf

sleep 2
supervisorctl status 
# Step 6: Keep the container running
tail -f /dev/null
