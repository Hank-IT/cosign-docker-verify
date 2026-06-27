#!/usr/bin/env python3

import sys, getopt, yaml, os, subprocess, shutil, re
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

ENV_VAR_PATTERN = re.compile(r'\$(\$|[A-Za-z_][A-Za-z0-9_]*|\{([^}]*)\})')

def interpolate_env(value):
   def split_expression(expression):
      for operator in (':-', ':?', ':+', '-', '?', '+'):
         if operator in expression:
            name, remainder = expression.split(operator, 1)
            return name, operator, remainder

      return expression, None, None

   def replace(match):
      token = match.group(1)

      if token == '$':
         return '$'

      if not token.startswith('{'):
         return os.environ.get(token, '')

      name, operator, remainder = split_expression(match.group(2))
      value = os.environ.get(name)
      is_set = value is not None
      is_non_empty = is_set and value != ''

      if operator is None:
         return value if is_set else ''

      if operator == ':-':
         return value if is_non_empty else remainder

      if operator == '-':
         return value if is_set else remainder

      if operator == ':?':
         if is_non_empty:
            return value

         raise ValueError(remainder or (name + ' is required'))

      if operator == '?':
         if is_set:
            return value

         raise ValueError(remainder or (name + ' is required'))

      if operator == ':+':
         return remainder if is_non_empty else ''

      if operator == '+':
         return remainder if is_set else ''

      return match.group(0)

   return ENV_VAR_PATTERN.sub(replace, value)

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
      candidateFiles = ['docker-compose.yaml', 'docker-compose.yml', 'compose.yaml', 'compose.yml']
      foundFiles = [f for f in candidateFiles if os.path.exists(f)]

      if len(foundFiles) == 0:
         print(bcolors.FAIL + "Oops! Could not find docker-compose file. Please specify path with --docker-compose=<path>" + bcolors.ENDC)
         sys.exit()
      elif len(foundFiles) > 1:
         print(bcolors.FAIL + "Oops! Multiple docker-compose files found (" + ", ".join(foundFiles) + "). It's unclear which to use, please specify the file with --docker-compose=<path>" + bcolors.ENDC)
         sys.exit()

      dockerComposePath = foundFiles[0]
      try:
         dockerCompose = open(dockerComposePath, 'r')
      except Exception:
         print(bcolors.FAIL + "Oops! Could not find docker-compose file at " + dockerComposePath + bcolors.ENDC)
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

               image = dockerComposeYaml['services'][service]['image']

               try:
                  interpolatedImage = interpolate_env(image)
               except ValueError as err:
                  print(bcolors.FAIL + "Oops! Service " + service + " image environment interpolation failed: " + str(err) + bcolors.ENDC)
                  continue

               eligibleServices.append({ 'service': service, 'image': interpolatedImage, 'key': localKey })

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
