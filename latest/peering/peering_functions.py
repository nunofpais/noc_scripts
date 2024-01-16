# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
import webbrowser as wb

from scripts.nunopais.peering.peering_dbquery import (
    asn_country,
    asn_info,
    get_children_data,
    get_interfaces_data,
)
from termcolor import colored, cprint

# =============================== Print Info Function =============================== #

# ISP PEER INFORMATION OUTPUT
def pr_info_print(isp, asn, isp_country):
    cprint("\n       PEERING INFO:        ", "green")
    print("+-----------+------------+")
    print(
        "{:>1}{:<10} | {:<35}\n{:>1}{:<10} | {:<35}\n{:>1}{:<10} | {:<35}".format(
            " ", "ISP", isp, " ", "ASN", asn, " ", "COUNTRY", isp_country
        )
    )
    print("+-----------+------------+\n")


# =============================== ASN Functions =============================== #


# Get country from ASN info
def isp_country(asn):
    name, country_code = asn_info(asn)
    isp_country = asn_country(country_code)
    return isp_country

    # =============================== Peering Functions =============================== #


def p2p_ip_data(parent_data, noc_input):
    # Check if local or remote IP for P2P sessions
    parent_id = str(parent_data[0].id)
    children_data = get_children_data(parent_id)
    for peering in children_data[0].children:
        if peering.derived_type == "DesiredInterfaceAddressV4Prefix":
            local_ip = peering.prefix.split("/")[0]
            pr_ae = peering.description
            pr_aes = [pr_ae]
        else:
            remote_ip = peering.prefix.split("/")[0]
            isp = peering.description.split("as")[0]
            asn = peering.pniv4prefix.as_no
    cprint(f"\n {noc_input} It's a Local IP\n") if noc_input in local_ip else cprint(
        f"\n {noc_input} It's a Remote IP\n", "blue"
    )

    return pr_aes, local_ip, remote_ip, asn, isp


# =============================== Interface Functions =============================== #

# Gets interfaces from a given PR_AE
def metroid_links_from_aes(pr_aes, asn):
    pr_ets = {}  # PR_AE -> list of interfaces
    links_print = []

    for pr_ae in pr_aes:
        pr = pr_ae.split(":")[0]
        links_print.append(
            "https://www.internalfb.com/intern/bunny/?q=%s" % "metroid+{}".format(pr_ae)
        )
        interfaces_data = get_interfaces_data(str(pr_ae))
        pr_ets[pr_ae] = []
        for interface in interfaces_data[0].aggregatedinterface.physicalinterfaces:
            pr_ets[pr_ae].append(interface.name)
            # print(interface.name)
            # pr_ets.append(interface.name)
            links_print.append(
                "https://www.internalfb.com/intern/bunny/?q=%s"
                % "metroid+{}:{}".format(pr, interface.name)
            )
            # bgp_command = f"show bgp summary | grep {interface.name}"
    # int_tshoot(pr_ets)

            # for pr in prs:
        # asn2 = " " + str(asn) + " "


    # for session in bgp_session:
        print(colored(f"\nBGP session for {pr}:", "green", attrs=["underline"]))
        command = f'show bgp summary | grep " {asn} "'
        os.system(f"ssh {pr} '{command}'")

    int_tshoot(pr_ets)

    for link in links_print:
        cprint(link, "blue")
        # wb.open(link)
    print()
    return links_print


# Runs commands on all interfaces of a given PR_AE
def int_tshoot(pr_ets):
    for pr_ae in pr_ets.keys():
        cprint(f"\nTroubleshooting -- {pr_ae} --\n", "red", attrs=["bold"])
        pr = pr_ae.split(":")[0]
        printing = ["OPTICS", "STATS"]
        printing = printing * len(pr_ets[pr_ae])
        for intf in pr_ets[pr_ae]:
            commands = []
            sintax = 'show interfaces {i} statistics | grep "Physical|Description|Link-level|Last|Input|Output"'.format(
                i=intf
            )
            sintax2 = "show interfaces diagnostics optics {i} | match dbm | except thre".format(
                i=intf
            )
            commands.append(sintax2)
            commands.append(sintax)

            idx = 0
            for command in commands:
                print(colored(f"{pr}:{intf} {printing[idx]}", attrs=["underline"]))
                os.system("ssh {pr} '{c}'".format(pr=pr, c=command))

                idx += 1
                print("\n")
