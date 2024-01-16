# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
import sys

from scripts.nunopais.peering.peering_dbquery import (
    get_parent_data,
    remote_ip_bgp_session,
)

from scripts.nunopais.peering.peering_functions import (
    isp_country,
    metroid_links_from_aes,
    p2p_ip_data,
    pr_info_print,
)
from termcolor import colored, cprint


# Get input - Peering IP / Peering Router Port
if len(sys.argv) == 3:
    peering_input = sys.argv[1]
    asn = str(sys.argv[2])
elif len(sys.argv) == 2:
    peering_input = sys.argv[1]
else:
    cprint("Please provide a peering input (IP / Peering Router Port)", "red")
    exit()

peering_input = peering_input.lower()

parent_data = get_parent_data(peering_input)
parent_data = [
    line for line in parent_data if line.prefix != "0.0.0.0/0"
]  # filter out 0.0.0.0/0

try:
    if parent_data[0].children[0].derived_type == "DesiredPNIV4Prefix":
        asn = parent_data[0].children[0].pniv4prefix.as_no
        isp_country = isp_country(asn)
        if parent_data[0].prefix_length >= 30:
            pr_aes, local_ip, remote_ip, asn, isp = p2p_ip_data(
                parent_data, peering_input
            )
            print(asn, isp_country, pr_aes, local_ip, remote_ip, asn, isp)
        # exit()
        if parent_data[0].prefix_length >= 20:
            pr_aes = []
            test_data = remote_ip_bgp_session(peering_input)
            for data in test_data:
                pr_aes.append(data.local_prefix.description)
            print(
                colored(
                    f"\n\nMultiple local IPs for remote IP: {peering_input}",
                    "red",
                    attrs=["underline"],
                )
            )
            isp = data.peer.name
            asn = data.peer.as_no
            prs = [pr_ae.split(":")[0] for pr_ae in pr_aes]
            # print(prs, isp, asn)

        # 1.2.1  Troubleshoot LAG interfaces
        links_print = metroid_links_from_aes(pr_aes, asn)
        # print(pr_aes)
        # for pr in prs:
        #     print(colored(f"\nBGP session for {pr}:", "green", attrs=["underline"]))
        #     # asn2 = " " + str(asn) + " "
        #     command = f'show bgp summary | grep " {asn} "'
        #     os.system(f"ssh {pr} '{command}'")


        pr_info_print(isp, asn, isp_country)
    else:  # local IP
        if parent_data[0].prefix_length >= 30:
            pr_aes, local_ip, remote_ip, asn, isp = p2p_ip_data(
                parent_data, peering_input
            )
            # prs = [pr_ae.split(":")[0] for pr_ae in pr_aes]
            isp_country = isp_country(asn)

            links_print = metroid_links_from_aes(pr_aes, asn)

            # for pr in prs:
            #     print(colored(f"\nBGP session for {pr}:", "green", attrs=["underline"]))
            #     # asn2 = " " + str(asn) + " "
            #     command = f'show bgp summary | grep " {asn} "'
            #     os.system(f"ssh {pr} '{command}'")
            # os.system(
            #     "fbm list --ip {} --asn {} --peertype ALL --fields asn,local_ip,remote_ip,state,count,limit,aggr_iface 2> /dev/null".format(
            #         remote_ip, asn
            #     )
            # )
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
                cprint(
                    "Multiple peer IPs found. Please get remote IP or use ASN instead.\n"
                )
except IndexError:  # No Parent Data
    cprint("NOT A PEERING IP", "red")
