# vsputils

Utilities for OpenVSP

## Python

Contains the `vsputils` package. Best installed locally.

## Docker

Dockerfiles to create docker images. Currently only creates an image able to run VSP via scripts (no GUI or python).

### Building an image

The context (i.e. the root of the building directory) has to contain the repo. Thus, with the following organization:

- OpenVSP
  - repo: clone of OpenVSP git repository
  - vsputils (where this file is located)
  
the running directory must be one level above this directory (i.e. at OpenVSP above).

```sh
docker build --build-arg REPO_PATH=./repo --network host -t openvsp:latest -f vsputils/docker/Dockerfile .
```

### Running an image

The simplest command:

```sh
docker run -it openvsp /bin/bash
```

This starts a terminal in the "machine" of the image. One can test that `vspaero` is available for instance.

The image has its working directory at `/tmp/wdir`. Thus, one should "volume" the directory where we have our model to there. VSPAERO will run there and create the output files there. Note that a script is needed for standalone runs. You either copy the script to the model directory, or create another volume pointing to the script directory and run it with the appropriate path.

For example, we have our model at `/home/me/models/ap.vsp3` and a script at `/home/me/scripts/af.vspscript`. Then the running command is:

```sh
docker run --rm -v /home/me/models:/tmp/wdir -v /home/me/scripts:/tmp/scr openvsp vspscript -script /tmp/scr/af.vspscript ap.vsp3 > stdout.log 2> stderr.log
```

The command above will redirect the outputs to the files _in the host_, not in the image.


## Scripts

Installation scripts, for ease of installation of OpenVSP on my machines.
