
# Minimal **Mesosphere DC/OS** v1.8 (with only 1 node)
##### ... (with tweak for running `slave` & a tiny `marathon-lb` on the `single` node)

### Prerequisites
- One VM only! (for a resource constrained lab or laptop)
- CentOS 7.2 Minimal + SELINUX Disabled + Firewall Disabled + IPv6 Disabled
- Docker 1.11.X with "--storage-driver=overlay"

### Configuration
| Host | Role | VM Size |
|----- |----- |-------- |
|mesos-mini-01 |bootstrap + master + slave + dcos-cli | 2 CPU, 6GB RAM, 60GB HDD

### Common script

```
# add docker repo and install docker
cat > /etc/yum.repos.d/docker.repo << '__EOF__'
[docker]
name=Docker Repository - Centos $releasever
baseurl=http://yum.dockerproject.org/repo/main/centos/$releasever
enabled=1
gpgcheck=1
gpgkey=http://yum.dockerproject.org/gpg
__EOF__

yum install -y https://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-8.noarch.rpm
yum install -y docker-engine-1.11.2 docker-engine-selinux-1.11.2 tar xz unzip curl ipset chrony nfs-utils

yum clean all

groupadd nogroup

mkdir -p /etc/systemd/system/docker.service.d

cat > /etc/systemd/system/docker.service.d/override.conf << '__EOF__'
[Service] 
ExecStart= 
ExecStart=/usr/bin/docker daemon --storage-driver=overlay --insecure-registry hub.sudhaker.com:5000 -H fd:// 
__EOF__

systemctl daemon-reload
systemctl enable docker

systemctl start docker

# if the default DNS doesn't resolve
tee -a /etc/hosts << '__EOF__'

192.168.0.173 mesos-single
__EOF__

```

### To be run for bootstrap
**Generate bootstrap**

```
mkdir /opt/dcos-setup && cd /opt/dcos-setup && curl -O https://downloads.dcos.io/dcos/stable/dcos_generate_config.sh
 
mkdir -p genconf
 
cat > genconf/ip-detect << '__EOF__'
#!/usr/bin/env bash
set -o nounset -o errexit
export PATH=/usr/sbin:/usr/bin:$PATH
echo $(ip addr show ens192 | grep -Eo '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
__EOF__
 
chmod 755 genconf/ip-detect
 
### VERY IMPORTANT: validate that the following ip-detect is working
### if not then follow https://dcos.io/docs/1.8/administration/installing/custom/advanced/
###   to get a working script, must work consistently on each & every node
./genconf/ip-detect

cat > genconf/config.yaml << '__EOF__'
---
bootstrap_url: http://mesos-single:8081       
cluster_name: dcos
exhibitor_storage_backend: static
master_discovery: static
master_list:
- 192.168.0.173
resolvers:
- 8.8.4.4
- 8.8.8.8
telemetry_enabled: 'false'
__EOF__
 
bash dcos_generate_config.sh
```

**Launch bootstrap**

```
docker pull nginx:alpine
docker run -d --restart=unless-stopped -p 8081:80 -v /opt/dcos-setup/genconf/serve:/usr/share/nginx/html:ro --name=dcos-bootstrap-nginx nginx:alpine
```

### To be run for {master}

```
mkdir -p /tmp/dcos && cd /tmp/dcos && curl -O http://mesos-single:8081/dcos_install.sh && bash dcos_install.sh master && cd -
```
**Install dcos-cli** (while we are waiting for master to come up).
```
mkdir -p ~/bin && cd ~/bin && curl -O https://downloads.dcos.io/binaries/cli/linux/x86-64/dcos-1.8/dcos && chmod 755 ~/bin/dcos && cd -
 
dcos config set core.dcos_url http://192.168.0.173
dcos auth login
```

### To be run for {slave}

```
export opt_mesos=$(ls -1d /opt/mesosphere/packages/mesos--*)
ln -s $opt_mesos/dcos.target.wants_slave/dcos-mesos-slave.service /etc/systemd/system
ln -s $opt_mesos/dcos.target.wants_slave/dcos-mesos-slave.service /etc/systemd/system/dcos.target.wants
systemctl start dcos-mesos-slave
```

### Install the tiny marathon-lb (0.1 CPU, 128mb RAM)
**IMPORTANT**: `dcos package` won’t let us install this minimal configuration, so we’ll use marathon!

**Export marathon json**

```
cat > marathon-lb-internal.json << '__EOF__'
{ "marathon-lb":{ "name": "marathon-lb-internal", "instances": 1, "haproxy-group": "internal", "role": "", "bind-http-https": false} }
__EOF__

dcos package describe --app --render marathon-lb --options=marathon-lb-internal.json > marathon-lb.json

```

**Edit the json, use sed or manually edit it**

```
sed -i 's/"cpus": 2/"cpus": 0.1/' marathon-lb.json
sed -i 's/ "mem": 1024/ "mem": 128/' marathon-lb.json
```

**Let `marathon` deploy this app**

```
dcos marathon app add marathon-lb.json
```

### Install the demo app (`dockercloud/hello-world`)

```
cat > dockercloud-hello-world.json << '__EOF__'
{
  "id": "dockercloud-hello-world",
  "container": {
    "type": "DOCKER",
    "docker": {
      "image": "dockercloud/hello-world",
      "network": "BRIDGE",
      "portMappings": [
        { "hostPort": 0, "containerPort": 80, "servicePort":10000 }
      ],
      "forcePullImage":true
    }
  },
  "instances": 2,
  "cpus": 0.1,
  "mem": 128,
  "healthChecks": [{
      "protocol": "HTTP",
      "path": "/",
      "portIndex": 0,
      "timeoutSeconds": 10,
      "gracePeriodSeconds": 10,
      "intervalSeconds": 2,
      "maxConsecutiveFailures": 10
  }],
  "labels":{
    "HAPROXY_GROUP":"internal"
  }
}
__EOF__

dcos marathon app add dockercloud-hello-world.json
```

> Browse to => http://192.168.0.173:10000/

> HAProxy stats at http://192.168.0.173:9090/haproxy?stats

