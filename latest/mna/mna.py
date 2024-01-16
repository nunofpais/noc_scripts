# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import sys

from scripts.nunopais.mna.mna_dbquery import cluster_peer_ip, get_parent_data

from scripts.nunopais.mna.mna_functions import cluster_function, ip_to_cluster_prefix
from termcolor import cprint

# Get input - IP / Cluster
if len(sys.argv) == 3:
    cluster_input = sys.argv[1]
    asn = str(sys.argv[2])
elif len(sys.argv) == 2:
    cluster_input = sys.argv[1]
else:
    cprint("Please provide a cluster input (IP / cluster name)", "red")
    exit()

cluster_input = cluster_input.lower()


if (
    (cluster_input[0] == "f" and cluster_input[-3] == "c")
    or (cluster_input[0] == "f" and cluster_input[-2] == "-")
    or (cluster_input[0] == "f" and cluster_input[-3] == "-")
):
    cluster_function(cluster_input)

else:  # ipaddress.ip_address(noc_input):

    try:
        parent_data = get_parent_data(cluster_input)
        parent_data = [
            line for line in parent_data if line.prefix != "0.0.0.0/0"
        ]  # filter out 0.0.0.0/0

        # 1. Check if Cache or Peering (Local or Remote IP)
        # 1.1  Check if it's Cache
        if "Vip" in parent_data[0].children[0].derived_type:
            # 1.1.1  Checking if is cache vIP
            ip_to_cluster_prefix(cluster_input)

        if "rsw1aa" in parent_data[0].children[0].description:
            # 1.1.2  Checking if is switch IP
            ip_to_cluster_prefix(cluster_input)
        else:
            cprint("No cluster found for that input", "red")

    except IndexError:  # No Parent Data
        cluster = cluster_peer_ip(
            cluster_input
        )  # check if cluster peer ip not in cluster prefix
        if cluster:
            cluster_function(cluster)
        else:
            ip_to_cluster_prefix(cluster_input)
