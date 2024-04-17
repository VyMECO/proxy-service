# Stage 1: Build 3proxy
FROM ubuntu:22.04 AS builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install dependencies
RUN apt-get update && apt-get install -y build-essential libevent-dev libssl-dev ethtool curl wget

# Create directory for 3proxy
RUN mkdir -p /usr/local/etc/3proxy

# Download and extract 3proxy source
WORKDIR /usr/local/etc/3proxy
RUN wget https://github.com/z3APA3A/3proxy/archive/0.9.3.tar.gz
RUN tar zxvf 0.9.3.tar.gz
RUN rm 0.9.3.tar.gz
RUN mv 3proxy-0.9.3/* . && rm -r 3proxy-0.9.3

# Build 3proxy
RUN make -f Makefile.Linux

# Stage 2: Python 3.7 image for Flask application
FROM python:3.7

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y supervisor iproute2
RUN pip3 install flask bs4 psutil supervisor requests

# Create directory for 3proxy in final image
RUN mkdir -p /app/3proxy

# Copy 3proxy binary from the builder stage
COPY --from=builder /usr/local/etc/3proxy/ /app/3proxy/

# Set permissions if necessary
RUN chmod +x /app/3proxy/bin/*

COPY ./agent/ /app/agent/

# Copy initialization script
COPY ./helper/ /app/helper/
COPY ./helper/supervisor_services.conf /etc/supervisor/conf.d/supervisor_services.conf 

RUN chmod +x /app/helper/*.py
RUN chmod +x /app/helper/*.sh

# Make the initialization script executable
#RUN chmod +x /app/helper/init.sh

# Execute the initialization script
CMD ["/app/helper/init.sh"]
