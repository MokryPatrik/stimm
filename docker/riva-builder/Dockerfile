FROM ubuntu:22.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
      expect \
      build-essential \
      python3.11 python3.11-dev python3-pip \
      apt-transport-https \
      ca-certificates \
      curl \
      gnupg \
      tzdata \
      wget \
      unzip && \
    ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI and Docker Compose (we’ll use host’s daemon via /var/run/docker.sock)
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && \
    echo "deb [arch=amd64] https://download.docker.com/linux/ubuntu jammy stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && apt-get install -y docker-ce-cli && \
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Install NGC CLI
# Install NGC CLI
# Install NGC CLI
RUN mkdir -p /opt/ngc && cd /opt/ngc && \
    apt-get update && apt-get install -y wget unzip && \
    wget --content-disposition \
      "https://api.ngc.nvidia.com/v2/resources/nvidia/ngc-apps/ngc_cli/versions/4.3.0/files/ngccli_linux.zip" -O ngccli_linux.zip && \
    unzip ngccli_linux.zip && \
    chmod u+x ngc-cli/ngc && \
    ln -s /opt/ngc/ngc-cli/ngc /usr/local/bin/ngc && \
    rm -f ngccli_linux.zip

COPY ./riva-builder-scripts /app/riva-builder-scripts
RUN chmod +x /app/riva-builder-scripts/*.sh /app/riva-builder-scripts/*.exp

ENTRYPOINT ["/bin/bash", "-c", "chmod +x /app/riva-builder-scripts/*.sh && /app/riva-builder-scripts/start-riva-builder.sh"]
