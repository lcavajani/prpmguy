# PRPMguy

The main purpose of this script is to create RPMs from Github PRs.
The PRs can be retrieved in two ways:
* by labels
* by their unique number

It is based on the [script](https://gitlab.suse.de/docker/automation/blob/master/scripts/create_project_from_pr.py) created by Jordi. 

In order to work with private repositories, the
environment variable `GITHUB_TOKEN` must be set.

The default configuration file is `prpmguy.yaml`


**Note for `velum` package**:

Remember that for this to be a valid package for a MR you need to update the sles12sp3-velum-image and the changelog-generator-data-sles12sp3-velum packages.

For the image, you need to increase the version and update the changelog with bscs.

For the data, see https://gitlab.suse.de/docker/DOCS/wikis/all-about-sle-images")

If this is just a test package, you can ignore this.


## Usage

```console
./prpmguy.py --help
usage: prpmguy.py [-h] [--conf-file [CONF_FILE]] [--oscrc-file [OSCRC_FILE]]
                  [--show-osc-commands]

Create RPMs from Github PRs.

optional arguments:
  -h, --help            show this help message and exit
  --conf-file [CONF_FILE]
                        Configuration file
  --oscrc-file [OSCRC_FILE]
                        osc configuration file
  --show-osc-commands   Show what osc commands are executed during run
```

Example:

```console
./prpmguy.py --oscrc-file /home/ci/.config/osc/oscrc --show-osc-commands
```

# Podman

**Build**

```console
sudo podman build -t prpmguy .
```

**Run**

Must be mounted in the container:
* environement var: $GITHUB_TOKEN
* mounted: configuration file
* mounted: oscrc file

```console
sudo podman run -ti --rm --env GITHUB_TOKEN=$GITHUB_TOKEN \
    -v "$(pwd)"/prpmguy.yaml:/app/prpmguy.yaml \
    -v "$(pwd)"/oscrc:/app/oscrc \
    rpmguy \
    --oscrc-file /app/oscrc
```

## Configuration example

**Create RPMs for both PRs by labels and standalone PRs**

```yaml
---
obs:
  username: "obs_user:test"
  api: "https://api.suse.de"
  osc_rcfile: "/home/ci/.oscrc"
  project: "SUSE:SLE-12-SP3:Update:Products:CASP30:Update"
  velum_image_name: "sles12sp3-velum-image"
  local_work_dir: ".workdir"

# Repositories which will be used when
# getting PRs by the labels
github:
  labels: ["needs qa", "needs QA"]
  repositories:
    - owner: "SUSE"
      name: "kubic-salt-security-fixes"
    - owner: "SUSE"
      name: "kubic-velum-security-fixes"

  # Standalone pull requests, labels are ignored
  pull_requests:
    - repo_owner: "SUSE"
      repo_name: "kubic-velum-security-fixes"
      number: 1
    - repo_owner: "SUSE"
      repo_name: "kubic-salt-security-fixes"
      number: 2
```


**Create RPMs for PRs by labels**

```yaml
---
obs:
  username: "obs_user:test"
  api: "https://api.suse.de"
  osc_rcfile: "/home/ci/.oscrc"
  project: "SUSE:SLE-12-SP3:Update:Products:CASP30:Update"
  velum_image_name: "sles12sp3-velum-image"
  local_work_dir: ".workdir"

# Repositories which will be used when
# getting PRs by the labels
github:
  labels: ["needs qa", "needs QA"]
  repositories:
    - owner: "SUSE"
      name: "kubic-salt-security-fixes"
    - owner: "SUSE"
      name: "kubic-velum-security-fixes"
```

**Create RPMs for standalone PRs**

```yaml
---
obs:
  username: "obs_user:test"
  api: "https://api.suse.de"
  osc_rcfile: "/home/ci/.oscrc"
  project: "SUSE:SLE-12-SP3:Update:Products:CASP30:Update"
  velum_image_name: "sles12sp3-velum-image"
  local_work_dir: ".workdir"

  # Standalone pull requests
  pull_requests:
    - repo_owner: "SUSE"
      repo_name: "kubic-velum-security-fixes"
      number: 1
    - repo_owner: "SUSE"
      repo_name: "kubic-salt-security-fixes"
      number: 2
```


