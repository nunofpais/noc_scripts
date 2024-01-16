# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# from scripts.nunopais.dbquery import *
import os
import sys
import webbrowser as wb

from scripts.nunopais.dbquery import (
    cluster_peer_ip,
    get_parent_data,
    remote_ip_bgp_session,
)

from scripts.nunopais.functions import (
    circuit_function,
    circuit_info_print,
    cluster_function,
    int_tshoot,
    ip_to_cluster_prefix,
    isp_country,
    metroid_links_from_aes,
    p2p_ip_data,
    pr_info_print,
    text,
)

"""
    Global script that takes a value and
    calls correct functions depending on input:
    Circuit, ASN, IP
"""


# Get input - IP, Cluster, Peering Router Port, Circuit ID
if len(sys.argv) == 3:
    noc_input = sys.argv[1]
    asn = str(sys.argv[2])
elif len(sys.argv) == 2:
    noc_input = sys.argv[1]
else:
    print(
        text.red(
            "Please provide an input (IP, cluster, peering router port, circuit ID)"
        )
    )
    exit()

noc_input = noc_input.lower()


# ================================= Defining input type ================================= #

# ================================= Circuit Section =========================== #

if noc_input.startswith("fc-"):  # noqa
    pr, ae, pr_ae, et, pr_et, asn, isp, circuit = circuit_function(noc_input)
    pr_ets = {pr_ae: [et]}
    int_tshoot(pr_ets)
    print(
        text.dblue(
            "https://www.internalfb.com/intern/bunny/?q=%s" % "metroid+{}".format(pr_et)
        )
    )
    wb.open(
        "https://www.internalfb.com/intern/bunny/?q=%s" % "metroid+{}".format(pr_et)
    )
    circuit_info_print(noc_input, pr_ae, et, asn, isp)

    # =============================== Cluster Section =============================== #

elif (
    (noc_input[0] == "f" and noc_input[-3] == "c")
    or (noc_input[0] == "f" and noc_input[-2] == "-")
    or (noc_input[0] == "f" and noc_input[-3] == "-")
):
    cluster_function(noc_input)

    # ================================= IP Section ================================= #

else:  # ipaddress.ip_address(noc_input):

    try:
        parent_data = get_parent_data(noc_input)
        parent_data = [
            line for line in parent_data if line.prefix != "0.0.0.0/0"
        ]  # filter out 0.0.0.0/0
        # 1. Check if Cache or Peering (Local or Remote IP)
        # 1.1  Check if it's Cache
        if "Vip" in parent_data[0].children[0].derived_type:
            # 1.1.1  Checking if is cache vIP
            ip_to_cluster_prefix(noc_input)

        elif "rsw1aa" in parent_data[0].children[0].description:
            # 1.1.2  Checking if is switch IP
            ip_to_cluster_prefix(noc_input)
        # 1.2  Check if it's Cache
        elif parent_data[0].children[0].derived_type == "DesiredPNIV4Prefix":
            asn = parent_data[0].children[0].pniv4prefix.as_no
            isp_country = isp_country(asn)
            if parent_data[0].prefix_length >= 30:
                pr_aes, local_ip, remote_ip, asn, isp = p2p_ip_data(
                    parent_data, noc_input
                )
            elif parent_data[0].prefix_length >= 20:
                pr_aes = []
                test_data = remote_ip_bgp_session(noc_input)
                for data in test_data:
                    pr_aes.append(data.local_prefix.description)
                local_ip = "Multiple local IPs"
                isp = data.peer.name

            # 1.2.1  Troubleshoot LAG interfaces
            links_print = metroid_links_from_aes(pr_aes)
            os.system(
                "fbm list --ip {} --asn {} --peertype ALL --fields asn,local_ip,remote_ip,state,count,limit,aggr_iface 2> /dev/null".format(
                    noc_input, asn
                )
            )

            pr_info_print(isp, asn, isp_country)
        else:  # local IP
            if parent_data[0].prefix_length >= 30:
                pr_aes, local_ip, remote_ip, asn, isp = p2p_ip_data(
                    parent_data, noc_input
                )
                isp_country = isp_country(asn)

                links_print = metroid_links_from_aes(pr_aes)
                os.system(
                    "fbm list --ip {} --asn {} --peertype ALL --fields asn,local_ip,remote_ip,state,count,limit,aggr_iface 2> /dev/null".format(
                        remote_ip, asn
                    )
                )
                pr_info_print(isp, asn, isp_country)

            else:
                try:
                    pr_ae = parent_data[0].children[0].description
                    device = pr_ae.split(":")[0]
                    pr_aes = [pr_ae]
                    metroid_links_from_aes(pr_aes)
                    os.system(
                        "fbm list --asn {} --device {} --fields asn,local_ip,remote_ip,state,count,limit,aggr_iface 2> /dev/null".format(
                            asn, device
                        )
                    )
                    print()
                except NameError:
                    print(
                        text.red(
                            "Multiple peer IPs found. Please get remote IP or use ASN instead.\n"
                        )
                    )

    except IndexError:  # No Parent Data
        cluster = cluster_peer_ip(
            noc_input
        )  # check if cluster peer ip not in cluster prefix
        if cluster:
            cluster_function(cluster)
        else:
            ip_to_cluster_prefix(noc_input)
