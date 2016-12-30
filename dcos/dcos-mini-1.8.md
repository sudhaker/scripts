
# Minimal **Mesosphere DC/OS** v1.8 (with only two nodes)
##### ... (with tweak for running a tiny `marathon-lb` on the `slave` node)

### Prerequisites
- Two VMs only! (for a resource constrained lab or laptop)
- CentOS 7.x Minimal + SELINUX Disabled + Firewall Disabled + IPv6 Disabled
- Docker 1.11.X with "--storage-driver=overlay"
- Catch-all DNS *.a172.sudhaker.com => 192.168.0.172

### Configuration
| Host | Role | VM Size |
|----- |----- |-------- |
|mesos-mini-01 |bootstrap + master + dcos-cli | 2 CPU, 4GB RAM, 60GB HDD
|mesos-mini-02 | the slave (hybrid) | 2 CPU, 4GB RAM, 60GB HDD

### Common script - To be run on every node
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

192.168.0.171 mesos-mini-01
192.168.0.172 mesos-mini-02
__EOF__
```
### To be run on node1 {bootstrap + master + dcos-cli}
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
bootstrap_url: http://mesos-mini-01:8081       
cluster_name: dcos-mini
exhibitor_storage_backend: static
master_discovery: static
master_list:
- 192.168.0.171
resolvers:
- 192.168.0.1
telemetry_enabled: 'false'
__EOF__
 
bash dcos_generate_config.sh
```
**Launch bootstrap**
```
docker pull nginx:alpine
docker run -d --restart=unless-stopped -p 8081:80 -v /opt/dcos-setup/genconf/serve:/usr/share/nginx/html:ro --name=dcos-bootstrap-nginx nginx:alpine
```
**Install master**
```
mkdir -p /tmp/dcos && cd /tmp/dcos && curl -O http://mesos-mini-01:8081/dcos_install.sh && bash dcos_install.sh master && cd -
```
**Install dcos-cli** (while we are waiting for master to come up).
```
mkdir -p ~/bin && cd ~/bin && curl -O https://downloads.dcos.io/binaries/cli/linux/x86-64/dcos-1.8/dcos && chmod 755 ~/bin/dcos && cd -
 
dcos config set core.dcos_url http://192.168.0.171
dcos auth login
```
### To be run on node2 {the hybrid slave}
```
mkdir -p /tmp/dcos && cd /tmp/dcos && curl -O http://mesos-mini-01:8081/dcos_install.sh && bash dcos_install.sh slave  && cd -
```
And then tweak it to support marathon-lb on it (thanks Vishnu for the ‘mesos-resource’ pointer).
```
systemctl kill -s SIGUSR1 dcos-mesos-slave
systemctl stop dcos-mesos-slave
unlink /var/lib/mesos/slave/meta/slaves/latest
```
Edit /var/lib/dcos/mesos-resources (add 80, 443)
```
sed -i 's/\[{"begin"/\[{"begin": 80, "end": 80}, {"begin": 443, "end": 443}, {"begin"/' /var/lib/dcos/mesos-resources
```
Re-initialize the slave (with required ports - 80,443)
```
systemctl start dcos-mesos-slave
```
### Install the tiny marathon-lb (0.1 CPU, 64mb RAM)
**IMPORTANT**: `dcos package` won’t let us install this minimal configuration, so we’ll use marathon!

**Export marathon json**
```
dcos package describe --app --render marathon-lb > marathon-lb.json
```
**Edit the json, use sed or manually edit it**
```
sed -i 's/"slave_public"/"*"/' marathon-lb.json
sed -i 's/"cpus": 2/"cpus": 0.1/' marathon-lb.json
sed -i 's/ "mem": 1024/ "mem": 64/' marathon-lb.json
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
        { "hostPort": 0, "containerPort": 80 }
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
    "HAPROXY_GROUP":"external",
    "HAPROXY_0_VHOST":"dockercloud-hello-world.a172.sudhaker.com"
  }
}
__EOF__

dcos marathon app add dockercloud-hello-world.json
```

> Browse to => http://dockercloud-hello-world.a172.sudhaker.com






