#!/usr/bin/python3

import argparse
import os
import logging
import re
import requests
import subprocess
import sys
import yaml

from collections import defaultdict


def parse_args():
    """ Parse command line arguments """
    parser = argparse.ArgumentParser(description="Create RPMs from Github PRs.")

    parser.add_argument("--conf-file", nargs="?", required=False,
                        default="./prpmguy.yaml", action="store",
                        help="Configuration file")
    parser.add_argument("--oscrc-file", nargs="?", required=False, action="store",
                        default=None,
                        help="osc configuration file")
    parser.add_argument("--show-osc-commands", required=False,
                        default=False, action="store_true",
                        help="Show what osc commands are executed during run")

    args = parser.parse_args()
    return(args)


def load_yaml(yaml_file):
    """ Load file and read yaml """
    try:
        with open(yaml_file, "r", encoding="utf-8") as f:
            content = yaml.load(f)
        return(content)
    except IOError as e:
        logging.error("I/O error: {0}".format(e))
        sys.exit()
    except yaml.YAMLError as ey:
        logging.error("Error in yaml file: {0}".format(ey))
        sys.exit()


class Report(object):
    """ Show a quick yaml report at the end of a run """
    def __init__(self):
        self.report = defaultdict(list)

    def add_to_report(self, pr, status, message=None):
        output = pr.me
        output.pop("patch")
        output.pop("patch_url")
        output.pop("number")
        output["url"] = pr.me["url"]

        if message:
            output["message"] = message

        self.report[status].append(output)

    def print_report(self):
        print("\n-------\nReports\n-------")
        print(yaml.dump(dict(self.report), default_flow_style=False))


def write_file(path, content, mode):
    """Write string or binary to file

    Parameters
    ----------
    path : str
    content : bytes|str
    mode : str
        Can be "wb" for bytes or "w" for strings.
    """
    try:
        with open(path, mode) as f:
            f.write(content)
    except IOError as e:
        logging.error("I/O error: {0}".format(e))


class GithubQl(object):
    """This class is used to run GraphQL query
    against Github API.

    Parameters
    ----------
    token : str
        Github token for authentication
    """
    token = None
    headers = None

    def __init__(self, token):
        self.http_url = "https://api.github.com/graphql"
        self.token = token
        self.http = requests.Session()
        self.headers = self.__define_headers()

    def __define_headers(self):
        if self.token:
            return {"Authorization": "Bearer {}".format(self.token)}

    def query(self, query=None, variables=None):
        """ Return a JSON from a GraphQL query """

        try:
            request = self.http.post(self.http_url,
                                     json={'query': query, 'variables': variables},
                                     headers=self.headers)
            request.raise_for_status()
            return request.json()
        except(ConnectionError, requests.HTTPError, requests.Timeout) as e:
            logging.error("connection failed: {0}".format(e))
            sys.exit()

    def __retrieve_pr_patch(self, url):
        """ Return patch in bytes """
        try:
            headers = self.headers
            headers["Accept"] = "application/vnd.github.VERSION.patch"
            request = self.http.get(url, headers=headers, allow_redirects=True)
            request.raise_for_status()
            return request.content
        except(ConnectionError, requests.HTTPError, requests.Timeout) as e:
            logging.error("connection failed: {0}".format(e))
            sys.exit()

    def retrieve_pr_by_number(self, repo_name, repo_owner, number):
        """Retrieve a single PR by its number.

        Returns
        -------
        dict
            Return the following or None. The dict is then enrich
            with patch_url, patch, repo_owner, repo_name  by `__add_data_pr`
            {
              'title': 'PR title',
              'number': 1,
              'url': 'https://github.com/OWNER/NAME/pull/1',
              'patch_url': 'https://api.github.com/repos/OWNER/NAME/pulls/1',
              'patch': b'PATCH',
              'repo_owner': 'OWNER',
              'repo_name': 'kNAME'
            }
        """

        query = """
        query($repo_owner: String!, $repo_name: String!, $number: Int!) {
          repository(owner: $repo_owner, name: $repo_name) {
            pullRequest(number: $number) {
              title
              number
              url
            }
          }
        }"""

        variables = {
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "number": int(number),
        }

        pr = self.query(query, variables)
        pr = pr["data"]["repository"]["pullRequest"]

        if pr:
            pr = self.__add_data_pr(pr, repo_name, repo_owner)

        return pr

    def retrieve_prs_by_label(self, repo_name, repo_owner, labels):
        """Retrieve several PRs by their labels.

        Returns
        -------
        list
            Return the following or None. The dict inside the list are then
            enrich with patch_url, patch, repo_owner, repo_name  by `__add_data_pr`
            [{
              'title': 'PR title',
              'number': 1,
              'url': 'https://github.com/OWNER/NAME/pull/1',
              'patch_url': 'https://api.github.com/repos/OWNER/NAME/pulls/1',
              'patch': b'PATCH',
              'repo_owner': 'OWNER',
              'repo_name': 'kNAME'
            },
            {
              'title': 'PR title',
              'number': 2,
              'url': 'https://github.com/OWNER/NAME/pull/2',
              'patch_url': 'https://api.github.com/repos/OWNER/NAME/pulls/2',
              'patch': b'PATCH',
              'repo_owner': 'OWNER',
              'repo_name': 'kNAME'
            }]
        """

        query = """
        query($repo_owner: String!, $repo_name: String!, $labels: [String!]) {
          repository(owner: $repo_owner, name: $repo_name) {
            pullRequests(last: 100, states: OPEN, labels: $labels) {
              edges {
                node {
                  title
                  number
                  url
                }
              }
            }
          }
        }"""

        variables = {
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "labels": labels,
        }

        prs = self.query(query, variables)
        prs = prs["data"]["repository"]["pullRequests"]["edges"]
        prs_clean = []

        if prs:
            for pr in prs:
                # Remove ["node"] key so we have the same
                # output as retrieve_pr_by_number
                prs_clean.append(pr["node"])

            for pr in prs_clean:
                self.__add_data_pr(pr, repo_name, repo_owner)

        return prs_clean

    def __add_data_pr(self, pr, repo_name, repo_owner):
        """ Enrich PR dict with patch_url, patch, repo_owner, repo_name """

        patch_url = "https://api.github.com/repos/{0}/{1}/pulls/{2}".format(
                    repo_owner, repo_name, pr["number"])
        pr["patch_url"] = patch_url
        pr["patch"] = self.__retrieve_pr_patch(patch_url)
        pr["repo_owner"] = repo_owner
        pr["repo_name"] = repo_name

        return pr


class PullRequest(object):
    """This class is used to make easier the use
    of PR properties in the class `Osc`
    """

    def __init__(self, pr):
        self.pr = pr

    @property
    def bscs(self):
        bsc_re = re.compile("(?<=bnc|bsc)#(\d+)")
        bsc = bsc_re.findall(self.title)
        bsc = list(set(bsc))
        bsc.sort()
        return bsc

    @property
    def me(self):
        return self.pr

    @property
    def number(self):
        return str(self.pr["number"])

    @property
    def package_name(self):
        if self.repo_name == "kubic-salt-security-fixes":
            return "kubernetes-salt"

        if self.repo_name == "kubic-velum-security-fixes":
            return "velum"

    @property
    def patch(self):
        return self.pr["patch"]

    @property
    def patch_name(self):
        return self.number + ".patch"

    @property
    def patch_url(self):
        return self.pr["patch_url"]

    @property
    def repo_owner(self):
        return self.pr["repo_owner"]

    @property
    def repo_name(self):
        return self.pr["repo_name"]

    @property
    def link(self):
        return "github.com/{0}/{1}/pull/{2}".format(self.repo_owner,
                                                    self.repo_name,
                                                    self.number)

    @property
    def title(self):
        return self.pr["title"]


class Osc(object):
    """This class is used to run osc commands in
    order to create the RPMs.

    Parameters
    ----------
    pr : dict
        Pull Request
    obs_conf : dict
        OBS Configuration
    """

    def __init__(self, pr, obs_conf, report):
        self.pr = pr
        self.api = obs_conf["api"]
        self.username = obs_conf["username"]
        self.osc_rcfile = obs_conf["osc_rcfile"]
        self.source_project = obs_conf["project"]
        self.velum_image_name = obs_conf["velum_image_name"]
        self.show_osc_commands = obs_conf["show_osc_commands"]

        #self.report = Report()
        self.report = report

        self.work_dir = obs_conf["local_work_dir"]
        self.pr_project_name = self.__pr_project_name()

    def osc(self, *args, **kwargs):
        """ Command line, shell out to osc """

        # check retcode by default unless explicitly set
        if not kwargs.get("check", None):
            kwargs['check'] = False
        else:
            kwargs['check'] = True

        options = list(args)

        # `-c /path/to/rcfile` must be at the beginning
        if self.osc_rcfile:
            options.insert(0, "-c {}".format(self.osc_rcfile))

        # Build arguments
        options = " ".join(options)
        cmd = "/usr/bin/osc -A {0} {1}".format(self.api,
                                               options)

        # Show the commands which are executed
        if self.show_osc_commands:
            logging.info(cmd)

        return subprocess.run(cmd, shell=True, **kwargs)

    def __pr_project_name(self):
        """ home:user:bsc_1234567 """
        pr_project = "home:" + self.username + ":test:bsc"
        for bsc in self.pr.bscs:
            pr_project += "_" + bsc
        return pr_project

    @property
    def local_project_path(self):
        """ /workdir/home:user:bsc_1234567 """
        return os.path.join(self.work_dir, self.pr_project_name)

    @property
    def local_package_path(self):
        """ home:user:bsc_1234567/package-name """
        return os.path.join(self.work_dir, self.pr_project_name, self.pr.package_name)

    def __package_has_changes(self):
        """Find changes in package by making a diff
        Returns true if there is a diff
        """
        diff = self.osc("diff",
                        cwd=self.local_package_path,
                        stdout=subprocess.PIPE)
        return diff.stdout

    def branch_package(self):
        """ Branch package on OBS """
        logging.info("Branching {0} {1} {2}".format(self.source_project,
                                                    self.pr.package_name,
                                                    self.pr_project_name))

        self.osc("branch",
                 self.source_project,
                 self.pr.package_name,
                 self.pr_project_name,
                 check=False)

        if self.pr.package_name == "velum":
            logging.info("Branching also {0}".format(self.velum_image_name))
            self.osc("branch",
                     self.source_project,
                     self.velum_image_name,
                     self.pr_project_name)

            logging.info("Aggregating image binaries")
            self.osc("aggregatepac -m containers=standard",
                     self.pr_project_name,
                     self.velum_image_name,
                     self.pr_project_name,
                     "aggregates")

    def __add_bsc_entry(self, bsc):
        logging.info("Adding entry about Fixing bsc#{0} in {1}.changes".format(bsc,
                                                                               self.pr.package_name))
        self.osc("vc -m", "'Fix bsc# {0} in {1}'".format(bsc, self.pr.package_name),
                 cwd=self.local_package_path)

    def check_out_package(self):
        """ Check out package locally """

        if not os.path.exists(self.local_package_path):
            logging.info("Cheking out")
            self.osc("checkout",
                     self.pr_project_name,
                     "-o", self.local_project_path)

        logging.info("Updating working copy")
        self.osc("update", cwd=self.local_package_path)

    def add_patch_in_package(self):
        """ Add patch to the package """
        # Write patch in package directory
        logging.info("Writing patch in package directory")
        patch_path = os.path.join(self.local_package_path, self.pr.patch_name)
        write_file(patch_path, self.pr.patch, "wb")

    def add_patch_in_package_spec_changes(self):
        """ Add patch in the spec file of the package """

        logging.info("Patching package: " + self.local_package_path)

        spec_file_name = self.pr.package_name + ".spec"
        spec_file_path = os.path.join(self.local_package_path,
                                      spec_file_name)

        patch_text = "Patch{0}: {1} \n".format(self.pr.number,
                                               self.pr.patch_name)
        patching_text = "patch -p1 --no-backup-if-mismatch < %{{P:{0}}}\n".format(self.pr.number)

        text, previous_line = "", ""
        patch_added, patching_added = False, False

        with open(spec_file_path, "r") as f:
            try:
                for line in f:
                    if patch_text not in line:
                        if previous_line.startswith("Source:"):
                            logging.info("Adding {0} in {1} file".format(patch_text,
                                                                         spec_file_name))
                            text += patch_text
                            patch_added = True
                    if patching_text not in line:
                        if previous_line.startswith("%setup"):
                            logging.info("Adding {0}".format(patching_text))
                            text += patching_text
                            patching_added = True
                    previous_line = line
                    text += line

                if patch_added or patching_added:
                    write_file(spec_file_path, text, "w")

                    logging.info("Marking patch to be added upon the next commit")
                    self.osc("add", self.pr.patch_name, cwd=self.local_package_path)
                    for bsc in self.pr.bscs:
                        self.__add_bsc_entry(bsc)
            except Exception as e:
                message = "Something went wrong adding the patch into the spec file"
                logging.error(message + e)
                self.report.add_to_report(self.pr,
                                          status="failed",
                                          message="ERROR: {}".format(message))

    def commit_package(self):
        if self.__package_has_changes():
            logging.info("Uploading to the repository server")
            self.osc("commit -m", self.pr.link, cwd=self.local_package_path)

            self.report.add_to_report(self.pr,
                                      status="success",
                                      message="Changes uploaded")

            logging.info("Success\n")
        else:
            logging.info("No changes found, nothing to do\nSuccess")
            self.report.add_to_report(self.pr,
                                      status="success",
                                      message="No changes found")


def main():
    # Default loglevel
    logging.basicConfig(level=logging.INFO)

    # Parse args and build configuration
    args = parse_args()

    conf = load_yaml(args.conf_file)
    obs_conf = conf["obs"]
    gh_conf = conf["github"]

    if obs_conf.get("osc_rcfile") is None:
        obs_conf["osc_rcfile"] = args.oscrc_file

    obs_conf["show_osc_commands"] = args.show_osc_commands

    local_work_dir = os.path.abspath(conf["obs"]["local_work_dir"])
    obs_conf["local_work_dir"] = local_work_dir

    # Create working directory where the packages will
    # be checked out
    if not os.path.exists(local_work_dir):
        os.makedirs(local_work_dir)

    # Retrieve Github Token from env var
    if os.environ.get("GITHUB_TOKEN") is not None:
        GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    else:
        GITHUB_TOKEN = None

    # Create client to run GraphQL queries
    client = GithubQl(token=GITHUB_TOKEN)

    report = Report()

    prs = []
    # Retrieve PRs by label
    if gh_conf.get("repositories", None):
        for r in gh_conf["repositories"]:
            prs += client.retrieve_prs_by_label(repo_owner=r["owner"],
                                                repo_name=r["name"],
                                                labels=gh_conf["labels"])

    # Retrieve PRs by number
    if gh_conf.get("pull_requests", None):
        for r in gh_conf["pull_requests"]:
            prs.append(client.retrieve_pr_by_number(repo_owner=r["repo_owner"],
                                                    repo_name=r["repo_name"],
                                                    number=r["number"]))

    if prs is not None:
        for pr in prs:
            print("================================")
            pr = PullRequest(pr)
            osc = Osc(pr, obs_conf, report)
            if not pr.bscs:
                logging.warning("Can not build RPM for PR: {0}".format(pr.link))
                logging.warning("BSC is missing")
                osc.report.add_to_report(pr, status="failed",
                                         message="BSC is missing")
                continue
            osc.branch_package()
            osc.check_out_package()
            osc.add_patch_in_package()
            osc.add_patch_in_package_spec_changes()
            osc.commit_package()

    osc.report.print_report()


if __name__ == "__main__":
    main()
