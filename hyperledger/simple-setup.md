## Setup a Hyperledger Fabric Cluster (4 nodes) using Docker

### Download the required `docker-compose.yml` file
```
curl -sO https://raw.githubusercontent.com/sudhaker/scripts/master/hyperledger/compose/peer-pbft.yml
curl -sO https://raw.githubusercontent.com/sudhaker/scripts/master/hyperledger/compose/docker-compose.yml
```

### Let compose start it.
```
docker-compose up -d
```

### Wait for few seconds and verify
```
[root@centos72 hyperledger]# docker ps
CONTAINER ID        IMAGE                                  COMMAND                  CREATED             STATUS              PORTS                                                           NAMES
0b51dd9494cf        hyperledger/fabric-peer:latest         "sh -c 'sleep 5; peer"   8 minutes ago       Up 8 minutes        7052-7053/tcp, 0.0.0.0:7350->7050/tcp, 0.0.0.0:7351->7051/tcp   hyperledger_vp3_1
38d69791182a        hyperledger/fabric-peer:latest         "sh -c 'sleep 5; peer"   8 minutes ago       Up 8 minutes        7052-7053/tcp, 0.0.0.0:7150->7050/tcp, 0.0.0.0:7151->7051/tcp   hyperledger_vp1_1
b46996b3d48f        hyperledger/fabric-peer:latest         "sh -c 'sleep 5; peer"   8 minutes ago       Up 8 minutes        7052-7053/tcp, 0.0.0.0:7250->7050/tcp, 0.0.0.0:7251->7051/tcp   hyperledger_vp2_1
a949f8ec58ee        hyperledger/fabric-peer:latest         "sh -c 'sleep 5; peer"   8 minutes ago       Up 8 minutes        0.0.0.0:7050-7051->7050-7051/tcp, 7052-7053/tcp                 hyperledger_vp0_1
f686048610f9        hyperledger/fabric-membersrvc:latest   "membersrvc"             8 minutes ago       Up 8 minutes        7054/tcp                                                        hyperledger_membersrvc_1
```

### Check peers
```
[root@centos72 hyperledger]# curl -s localhost:7050/network/peers
{"peers":[{"ID":{"name":"vp3"},"address":"172.17.0.4:7051","type":1,"pkiID":"3kjeVpSiqeCBhmpBTdT7Xs2nQm4+6vpcEUIWW4lxQIU="},{"ID":{"name":"vp1"},"address":"172.17.0.5:7051","type":1,"pkiID":"/YYq0JzVvUS+tc5ERPPrKnr+jWBFWuiH9uP0NCEG1yk="},{"ID":{"name":"vp2"},"address":"172.17.0.6:7051","type":1,"pkiID":"QderaxSTQ6qz4hTAwO09ERd3232p8t1AbGo+RqMXqWg="},{"ID":{"name":"vp0"},"address":"172.17.0.3:7051","type":1,"pkiID":"HCqHdwXH+rRq+2sZorkAlRthxwlGH57hmguPuo03U9A="}]}

```

### Here is our genesis block.
```
[root@centos72 hyperledger]# curl localhost:7050/chain
{"height":1,"currentBlockHash":"RrndKwuojRMjOz/rdD7rJD/NUupiuBuCtQwnZG7Vdi/XXcTd2MDyAMsFAZ1ntZL2/IIcSUeatIZAKS6ss7fEvg=="}
```

... more to come
