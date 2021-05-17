import subprocess
import shlex
import time
import re


class ExpressVPNError(Exception):
      def __init__(self, msg, errno=None):
          self.errno = errno
          self.msg = msg

      def get_msg(self):
          # remove unnecessary formatting, such as red color etc.
          return self.msg.decode().replace("[1;32;49m", "").replace("[0;31;49m", "").replace("[0;33;49m", "").replace("[?25l", "").replace("[0m", "").replace("\x1b", "").strip("\n")

      def get_errno(self):
          return self.errno

      def __str__(self):
          return self.get_msg()


def run_command(cmd, timeout=0):
    if timeout > 0:
        process = subprocess.run(shlex.split(cmd),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 timeout=timeout)
    else:
        process = subprocess.run(shlex.split(cmd),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)

    if process.returncode != 0:
        raise ExpressVPNError(process.stdout, process.returncode)

    return process.stdout.decode().replace("[1;32;49m", "").replace("[0;31;49m", "").replace("[0;33;49m", "").replace("[?25l", "").replace("[0m", "").replace("\x1b", "")


def status():
    return run_command("expressvpn status")


def connect(server_name, timeout=30):
    run_command("expressvpn connect " + server_name, timeout=timeout)


def disconnect(timeout=30):
    run_command("expressvpn disconnect", timeout=timeout)


def refresh(timeout=30):
    run_command("expressvpn refresh", timeout=timeout)


def version():
    return run_command("expressvpn --version")


def is_activated():
    return "Not Activated" not in status()


def is_connected():
    return "Connected to" in status()


def is_not_connected():
    return "Not Connected" in status()


def is_connecting():
    return "Connecting..." in status()


def connected_location():
    if is_connected():
        status_msg = run_command("expressvpn status")
        for line in status_msg.split("\n"):
            if "Connected to" in line:
                index = line.rfind("Connected to")
                return line[index + len("Connected to")+1:]

    return "Not connected"


def get_location(alias):
    servers = list_servers(recommended=False)
    for server in servers:
        if server["alias"] == alias:
            return server["location"]
    else:
        return None


def get_alias(location):
    servers = list_servers(recommended=False)
    for server in servers:
        if server["location"] == location:
            return server["alias"]
    else:
        return None


def smart_location():
    return alias_location("smart")


def list_servers(recommended=True):
    vpn_list = run_command("expressvpn list all").split("\n")

    # removes initial lines not containing server information
    while vpn_list != [] and "----" not in vpn_list.pop(0):
        continue

    server_list = []
    # loop over all servers and extract alias and location
    for line in vpn_list:
        line_split = re.split("\s\s+" , "  ".join(line.split(" ", 1)))
        # skip line if it is not a server
        if len(line_split) < 2:
            continue

        if (not recommended or line_split[-1] == "Y"):
            alias = line_split[0]
            location = line_split[-2]
            # Bosnia and Herzegovina is a special case
            if alias == "ba":
                location = "Bosnia and Herzegovina"
            server_list.append({"alias": alias, "location": location})

    return server_list


def preference_status(preference):
    return run_command("expressvpn preferences " + preference)


def set_preference(preference, value):
    if preference_status(preference).strip("\n") != value:
        run_command("expressvpn preferences set " + preference + " " + value)
