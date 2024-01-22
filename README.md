# cosign-docker-verify
Helper script to verify Docker images using cosign and docker-compose

# Dependencies
 - Python >=3.7
 - python3-yaml
 - python3-dotenv
 - cosign

# Installation on apt based sytems

```
apt install git python3-yaml python3-dotenv
git clone https://github.com/Hank-IT/cosign-docker-verify.git /opt/cosign-docker-verify
```

# Docker-compose api
The script reads labels of docker-compose service definitions, if you wish to enable verification for a service add the following label:
```
cosign.verify=true
```

The script also allows you to directly specify a verification key:
```
cosign.verify=hashivault://<key-name>
```

The script also expands environment variables used in the "image" property of the service definition. System variables and .env variables are used.

# Usage

## docker-compose
The script tries to find the docker-compose file in the current directory by the following names: `docker-compose.yml` `docker-compose.yaml`.
If your docker-compose file is named differently you have to specify the name using:
```
./verify.py --docker-compose=<path>
```

## With global key for all services:
```
./verify.py -k <key>
```

## With per service key from docker-compose:
```
./verify.py
```

## Ignore cosign transparency log:
```
./verify.py --private-infrastructure
```
