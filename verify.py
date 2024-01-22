#!/usr/bin/env python3

import sys, getopt, yaml, os, subprocess, shutil
from dotenv import load_dotenv

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

load_dotenv(os.getcwd() + '/.env')

def main(argv):
   dockerComposePath = ''
   key = ''
   ignoreTlog = False

   cosign = shutil.which("cosign")

   if cosign is None:
     print(bcolors.FAIL + "This script requires cosign. Please install it." + bcolors.ENDC)
     sys.exit()

   opts, args = getopt.getopt(argv,"hk:i",["docker-compose=","private-infrastructure "])

   for opt, arg in opts:
      if opt == '-h':
         print(bcolors.OKBLUE + 'verify.py -k <key> --docker-compose=<docker-compose> --private-infrastructure ' + bcolors.ENDC)
         sys.exit()
      elif opt in '-k':
         key = arg
      elif opt in ("--docker-compose"):
         dockerComposePath = arg
      elif opt in ("--private-infrastructure "):
         ignoreTlog = True

   if key == '':
     print(bcolors.WARNING + "Global key not specified. Will try to get key from docker-compose." + bcolors.ENDC)

   if dockerComposePath != '':
      try:
         dockerCompose = open(dockerComposePath, 'r')
      except Exception:
         print(bcolors.FAIL + "Oops! Could not find docker-compose file at " + dockerComposePath + bcolors.ENDC)
         sys.exit()
   else:
      try:
         dockerCompose = open('docker-compose.yaml', 'r')
      except Exception:
         try:
            dockerCompose = open('docker-compose.yml', 'r')
         except Exception:
            print("(bcolors.FAIL + Oops! Could not find docker-compose file. Please specify path with --docker-compose=<path>" + bcolors.ENDC)
            sys.exit()

   dockerComposeYaml = yaml.safe_load(dockerCompose)

   eligibleServices = []

   for service in dockerComposeYaml['services']:
      if "labels" in dockerComposeYaml['services'][service]:
         for label in dockerComposeYaml['services'][service]['labels']:
            if "cosign.verify=" in label:
               if key == '' and label[14:] != 'true':
                 localKey = label[14:]
               else:
                 localKey = key

               image = dockerComposeYaml['services'][service]['image'].replace(':?err', '')

               eligibleServices.append({ 'service': service, 'image': os.path.expandvars(image), 'key': localKey })

   for eligibleService in eligibleServices:
       if eligibleService['key'] == '':
          print(bcolors.FAIL + "Oops! Service " + eligibleService['service'] + " has no key. Please specify global key with -k or use cosign.key= label." + bcolors.ENDC)
          continue

       try:
          result = subprocess.run(['cosign', 'triangulate', eligibleService['image'], '--type=digest'], stdout=subprocess.PIPE, check=True)
       except Exception:
          print(bcolors.FAIL + "Oops! Service " + eligibleService['service'] + " returned non-zero exited code while getting digest." + bcolors.ENDC)
          continue

       digest = result.stdout.decode('utf-8').rstrip()

       print(bcolors.OKBLUE + "Calculated digest for service " + bcolors.OKCYAN + eligibleService['service'] + bcolors.ENDC + bcolors.OKBLUE + " as " + bcolors.OKCYAN + digest + bcolors.ENDC)

       print(bcolors.OKBLUE + "Verifying service " + bcolors.OKCYAN + eligibleService['service'] + bcolors.ENDC)

       try:
          command = ['cosign', 'verify', '--private-infrastructure ', '--key', eligibleService['key'], digest] if ignoreTlog else ['cosign', 'verify', '--key', eligibleService['key'], digest]

          result = subprocess.run(command, stdout=subprocess.PIPE, check=True, capture_output=False)
          print(result.stdout.decode('utf-8'))

       except Exception:
          print(bcolors.FAIL + "Oops! Service " + eligibleService['service'] + " failed verification." + bcolors.ENDC)
          print(result.stdout.decode('utf-8'))
          print("\n")
          continue

if __name__ == "__main__":
   main(sys.argv[1:])
