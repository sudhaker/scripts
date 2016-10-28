## Setup a Hyperledger Fabric Cluster (4 nodes) using Docker

### Download the required `docker-compose.yml` file
```
curl -sO https://raw.githubusercontent.com/sudhaker/scripts/master/hyperledger/compose/docker-compose.yml
```

### Let compose start it.
```
docker-compose up -d
```

### Wait for few seconds and verify
```
[root@centos72 hyperledger]# docker ps
CONTAINER ID        IMAGE                           COMMAND                  CREATED             STATUS              PORTS                                                                    NAMES
d9a4d3249204        hyperledger/fabric-peer         "sh -c 'sleep 5; peer"   12 minutes ago      Up 12 minutes       0.0.0.0:7350->7050/tcp, 0.0.0.0:7351->7051/tcp, 0.0.0.0:7353->7053/tcp   hyperledger_vp3_1
085a4e7f30a2        hyperledger/fabric-peer         "sh -c 'sleep 5; peer"   12 minutes ago      Up 12 minutes       0.0.0.0:7050-7051->7050-7051/tcp, 0.0.0.0:7053->7053/tcp                 hyperledger_vp0_1
43d86a524b19        hyperledger/fabric-peer         "sh -c 'sleep 5; peer"   12 minutes ago      Up 12 minutes       0.0.0.0:7150->7050/tcp, 0.0.0.0:7151->7051/tcp, 0.0.0.0:7153->7053/tcp   hyperledger_vp1_1
020857cf8443        hyperledger/fabric-peer         "sh -c 'sleep 5; peer"   12 minutes ago      Up 12 minutes       0.0.0.0:7250->7050/tcp, 0.0.0.0:7251->7051/tcp, 0.0.0.0:7253->7053/tcp   hyperledger_vp2_1
6a490fc1e772        hyperledger/fabric-membersrvc   "membersrvc"             12 minutes ago      Up 12 minutes       0.0.0.0:7054->7054/tcp                                                   hyperledger_membersrvc_1
```

### Here is our genesis block.
```
[root@centos72 hyperledger]# curl localhost:7050/chain
{"height":1,"currentBlockHash":"RrndKwuojRMjOz/rdD7rJD/NUupiuBuCtQwnZG7Vdi/XXcTd2MDyAMsFAZ1ntZL2/IIcSUeatIZAKS6ss7fEvg=="}
[root@centos72 hyperledger]# curl localhost:7150/chain
{"height":1,"currentBlockHash":"RrndKwuojRMjOz/rdD7rJD/NUupiuBuCtQwnZG7Vdi/XXcTd2MDyAMsFAZ1ntZL2/IIcSUeatIZAKS6ss7fEvg=="}
[root@centos72 hyperledger]# curl localhost:7250/chain
{"height":1,"currentBlockHash":"RrndKwuojRMjOz/rdD7rJD/NUupiuBuCtQwnZG7Vdi/XXcTd2MDyAMsFAZ1ntZL2/IIcSUeatIZAKS6ss7fEvg=="}
[root@centos72 hyperledger]# curl localhost:7350/chain
{"height":1,"currentBlockHash":"RrndKwuojRMjOz/rdD7rJD/NUupiuBuCtQwnZG7Vdi/XXcTd2MDyAMsFAZ1ntZL2/IIcSUeatIZAKS6ss7fEvg=="}
[root@centos72 hyperledger]# 
```

... more to come
