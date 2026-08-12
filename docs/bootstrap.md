# bootstrap

the actual vuplix cli entrypoint (`bin/vulpix`) is the main character of this repository; making it
available to the system/user is the goal. it requires three things to run successfully:

1. access to the following commands: `bash` and `yq`
2. the `VULPIX` environmental variable, which should contain the install location (i.e. wherever
   this repo was cloned to)

with these requirements, `bootstrap.sh` has this outline:

1. determine desired install location and download or clone this repo to it
2. bootstrap yq
3. create initial `blueprint.yaml` and configuration scripts (these scripts setup global env file;
   including `VULPIX` env var)
4. run `bin/vulpix` for the first time to clean everything up and run initial config scripts

## dependency bootstrap

see [manual manager](../library/managers/manual/README.md#significance-during-bootstrap) for
implmentation details.

### bash

#### linux

for linux, it's up to you or your os to install bash, because its often intertwined with the os.

#### windows

there exists `bootstrap.ps1`, which is a wrapper around `bootstrap.sh`. it:

1. checks for bash and not found, installs it through MSYS2
2. downloads and runs `bootstrap.sh`
