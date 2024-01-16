# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import asyncio
import os
import re
import sys
import webbrowser as wb
from subprocess import PIPE, run

from libfb.py.employee import get_full_name
from scripts.nunopais.dbquery import (
    asn_country,
    asn_info,
    circuit_finder,
    cluster_cgnat,
    cluster_country,
    cluster_infos,
    cluster_ips,
    cluster_peer,
    get_children_data,
    get_interfaces_data,
    scuba_emetro,
)
from ti.platform.fna.bgp import get_bgp_table
from ti.platform.fnacli.cmds.glb.status import _get_fna_glb_status


# ================================ Text Manipulation ================================ #

# Colorize text


class text(object):
    """
    Text formatting for cli output
    """

    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    WHITE = "\033[38;5;231m"
    GREEN = "\033[38;5;46m"
    DGREEN = "\033[38;5;34m"
    RED = "\033[38;5;196m"
    DRED = "\033[38;5;124m"
    YELLOW = "\033[38;5;226m"
    BLUE = "\033[38;5;33m"
    DBLUE = "\033[38;5;21m"
    END = "\033[0;0m"

    def bold(self: str) -> str:
        return f"{text.BOLD}{self}{text.END}"

    def underline(self: str) -> str:
        return f"{text.UNDERLINE}{self}{text.END}"

    def white(self: str) -> str:
        return f"{text.WHITE}{self}{text.END}"

    def green(self: str) -> str:
        return f"{text.GREEN}{self}{text.END}"

    def dgreen(self: str) -> str:
        return f"{text.DGREEN}{self}{text.END}"

    def red(self: str) -> str:
        return f"{text.RED}{self}{text.END}"

    def dred(self: str) -> str:
        return f"{text.DRED}{self}{text.END}"

    def yellow(self: str) -> str:
        return f"{text.YELLOW}{self}{text.END}"

    def blue(self: str) -> str:
        return f"{text.BLUE}{self}{text.END}"

    def dblue(self: str) -> str:
        return f"{text.DBLUE}{self}{text.END}"


# ================================= MAIN FUNCTIONS ================================== #

# =============================== Print Info Function =============================== #


# CLUSTER INFORMATION OUTPUT
def cluster_info_print(
    cluster,
    asn,
    isp,
    ipv4_prefix,
    ipv6_prefix,
    ipv4_peer,
    ipv6_peer,
    pop,
    as_path,
    region,
    isp_country,
    isp_address,
    isp_city,
    isp_state,
    cgnat_config,
    esm,
    ndm,
    recommendation,
):
    print(text.dgreen("\n      CLUSTER INFO:        "))
    print("+---------------+-----------------------------+")
    print(
        "{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n".format(
            " ",
            "Cluster",
            cluster,
            " ",
            "ISP",
            isp,
            " ",
            "ASN",
            asn,
            " ",
            "IPv4 IP",
            ipv4_peer,
            " ",
            "IPv6 IP",
            ipv6_peer,
            " ",
            "IPv4 prefix",
            ipv4_prefix,
            " ",
            "IPv6 prefix",
            ipv6_prefix,
        )
    )
    print(
        "{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n".format(
            " ", "POP", pop, " ", "AS Path", str(as_path)
        )
    )
    print(
        "{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n".format(
            " ",
            "Region",
            region,
            " ",
            "Country",
            isp_country,
            " ",
            "Adress",
            isp_address,
            " ",
            "City",
            isp_city,
            " ",
            "State",
            isp_state,
        )
    )
    print(
        "{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n{:>1}{:<14} | {:<45}\n".format(
            " ", "CGNat", cgnat_config, " ", "ESM", esm, " ", "NDM", ndm
        )
    )
    print("{:>1}{:<14} | {:<45}".format(" ", "Recommendation", recommendation))
    print("+---------------+-----------------------------+\n")


# ISP PEER INFORMATION OUTPUT
def pr_info_print(isp, asn, isp_country):
    print(text.dgreen("\n       PEERING INFO:        "))
    print("+-----------+------------+")
    print(
        "{:>1}{:<10} | {:<35}\n{:>1}{:<10} | {:<35}\n{:>1}{:<10} | {:<35}".format(
            " ", "ISP", isp, " ", "ASN", asn, " ", "COUNTRY", isp_country
        )
    )
    print("+-----------+------------+\n")


# CIRCUIT INFORMATION OUTPUT
def circuit_info_print(circuit, pr_ae, et, asn, isp):
    print(text.dgreen("\n       PEERING INFO:        "))
    print("+-----------+-----------+")
    print(
        "{:>1}{:<10} | {:<35}\n{:>1}{:<10} | {:<35}\n{:>1}{:<10} | {:<35}\n{:>1}{:<10} | {:<35}\n{:>1}{:<10} | {:<35}".format(
            " ",
            "CIRCUIT",
            circuit.upper(),
            " ",
            "LAG",
            pr_ae,
            " ",
            "INTERFACE",
            et,
            " ",
            "ASN",
            asn,
            " ",
            "ISP",
            isp,
        )
    )
    print("+-----------+-----------+\n")

    # =============================== Circuit Functions =============================== #


def circuit_function(circuit_id):
    circuit = circuit_finder(circuit_id)
    pr, ae, pr_ae, et, pr_et, asn, isp = (
        circuit["pr_ae"].split(":")[0],
        circuit["ae"],
        circuit["pr_ae"],
        circuit["et"],
        circuit["pr_et"],
        circuit["asn"],
        circuit["isp"],
    )
    print(f"\n\nCircuit Device: {pr}\nPort-channel: {ae}\nCircuit Interface: {et}\n")
    return pr, ae, pr_ae, et, pr_et, asn, isp, circuit

    # =============================== Cluster Functions =============================== #


# get cluster naming standard (ex. flis8c01)
def cluster_name(var):
    if "-" in var or "." in var:
        datacenter, cluster_num = re.split("[-.]", var)
        cluster_number = [
            "0" + cluster_num[-1] if len(cluster_num) < 2 else cluster_num
        ][0]
        cluster = datacenter + "c" + cluster_number
        cluster_num = [
            cluster_number[-1] if cluster_number[-2] == "0" else cluster_number
        ][0]
    elif var[-3] == "c":
        cluster, datacenter = var, var[:-3]
        cluster_number = var[-2:]
        cluster_num = [
            cluster_number[-1] if cluster_number[-2] == "0" else cluster_number
        ][0]
    else:
        raise Exception(text.red("CLUSTER NAME NOT VALID"))
    cluster_standard = (datacenter + "-" + cluster_num).upper()
    return cluster, datacenter, cluster_num, cluster_number, cluster_standard


def ip_to_cluster_prefix(noc_input):
    ip_short, last_oct = noc_input.rsplit(".", 1)
    cluster_prefix = (
        ip_short
        + "."
        + [
            "0/26"
            if int(last_oct) < 64
            else ("64/26" if int(last_oct) < 128 else "128/26")
        ][0]
    )  # Get the prefix of the cluster
    cluster = cluster_peer(noc_input, cluster_prefix)
    cluster = [
        str(cluster[0][0]) + "-" + str(cluster[0][1])
        if len(cluster) > 0
        else sys.exit(text.red("\nIP NOT FOUND\n"))
    ][0]
    cluster_function(cluster)
    exit()


def cluster_testing(cluster, cluster_number, datacenter):
    cluster_bgp_table = asyncio.run(get_bgp_table(cluster))
    cluster_bgp = cluster_bgp_table.splitlines()[
        1:
    ]  # Getting bgp table and stripping columns on top
    sessions = []
    for line in cluster_bgp:
        session = line.split("<")[1].split(">")[0]
        sessions.append(session)
    ipv = ["IPv4", "IPv6"]
    idx = 0
    print()
    if len(sessions) < 3:
        for session in sessions:
            if session != "ESTABLISHED":
                print(text.red(f"{ipv[idx]} session is "), end=" ")
                print(f"{session}")
            else:
                print(f"{ipv[idx]} session is ", end=" ")
                print(text.dgreen(f"{session}"))
            idx += 1
    else:
        print(text.red("\nWARNING:"))
        print(text.dred("Cluster is MP-FNA multipeer fna"))

    # Check if hosts are up
    hosts = run(
        f"\nserf get status=STANDBY,name=fna0%.{cluster_number}.{datacenter}.%,mac=--distinct --fields name,status,maintenance_status,serial_number,mac,nics.ip_addr -t -n",
        shell=True,
        stdout=PIPE,
        encoding="utf-8",
    ).stdout
    standby_hosts = hosts
    hosts = hosts.splitlines()

    if hosts:
        print(text.red("\nThe following hosts are down:"))
        print(f"{standby_hosts}")
    else:
        print(text.dgreen("\nAll hosts are UP"))

    # GLB Status
    glb_statuses = asyncio.run(_get_fna_glb_status([f"{cluster}"]))[0]
    vips_health = ["yes" for line in glb_statuses if line["health"] == "no"]
    print(text.red("Following VIPs not healthy")) if vips_health else print(
        text.dgreen("VIPs are healthy")
    )

    for line in glb_statuses:
        if line["health"] == "no":
            print(
                "{0:25} {1:30} {2:50}".format(
                    line["glb_name"], line["vip_ip"], line["cromwellbesthealth_reason"]
                )
            )


def cluster_links(cluster):
    cluster_site, cluster_num = cluster.rsplit("c", 1)
    # Cluster Health
    url = "https://www.internalfb.com/intern/bunny/?q=%s" % "ech {c}".format(c=cluster)
    # Tupperware
    url2 = "https://www.internalfb.com/intern/bunny/?q=%s" % "tw {c}".format(c=cluster)
    # Dyndash
    url3 = "https://www.internalfb.com/intern/dyndash/traffic_infra/flb?mode_dyndash=minutes&minute_value_dyndash=1440&from_time_dyndash=&to_time_dyndash=&tpm_flb=flb.prod.{c}".format(
        c=cluster
    )
    # Amount of traffic served from cluster
    url4 = "https://www.internalfb.com/intern/scuba/query/?dataset=netflow&pool=uber&view=Area&drillstate=%7B%22purposes%22%3A[]%2C%22sampleCols%22%3A[]%2C%22cols%22%3A[%22bps%22]%2C%22derivedCols%22%3A[]%2C%22mappedCols%22%3A[]%2C%22enumCols%22%3A[]%2C%22return_remainder%22%3Afalse%2C%22should_pivot%22%3Afalse%2C%22is_timeseries%22%3Afalse%2C%22hideEmptyColumns%22%3Afalse%2C%22start%22%3A%22-1%20day%22%2C%22end%22%3A%22now%22%2C%22timezone%22%3A%22Europe%2FLondon%22%2C%22compare%22%3A[]%2C%22minBucketSamples%22%3A%22%22%2C%22samplingRatio%22%3A%221%22%2C%22dimensions%22%3A[%22type_new%22%2C%22outiface%22]%2C%22metric%22%3A%22sumratemin%22%2C%22top%22%3A%2220%22%2C%22axes%22%3A%22linked%22%2C%22time_bucket%22%3A%22fine%22%2C%22smoothing_bucket%22%3A%221%22%2C%22scale_type%22%3A%22absolute%22%2C%22compare_mode%22%3A%22normal%22%2C%22overlay_types%22%3A[]%2C%22markers%22%3A%22%22%2C%22custom_title%22%3A%22%22%2C%22area%22%3A%22normal%22%2C%22aggregateList%22%3A[]%2C%22param_dimensions%22%3A[%7B%22dim%22%3A%22dthruas_ord%22%2C%22op%22%3A%22all%22%2C%22param%22%3A%221%22%2C%22anchor%22%3A%220%22%7D]%2C%22modifiers%22%3A[]%2C%22order%22%3A%22bps%22%2C%22order_desc%22%3Atrue%2C%22filterMode%22%3A%22DEFAULT%22%2C%22constraints%22%3A[[%7B%22column%22%3A%22outiface%22%2C%22op%22%3A%22eq%22%2C%22value%22%3A[%22[%5C%22rsw1aa.{site}.{cluster}%3APort-Channel1%5C%22%2C%5C%22fpr{site}.{cluster}%3APort-Channel2%5C%22]%22]%7D]]%2C%22c_constraints%22%3A[[]]%2C%22b_constraints%22%3A[[]]%7D&normalized=1651154184&do_not_redirect=1".format(
        cluster=cluster_site, site=cluster_num
    )

    # Single prefix served from where?
    url5 = "https://www.internalfb.com/intern/scuba/query/?dataset=netflow&pool=uber&view=Area&drillstate=%7B%22purposes%22%3A[]%2C%22sampleCols%22%3A[]%2C%22cols%22%3A[%22bps%22]%2C%22derivedCols%22%3A[]%2C%22mappedCols%22%3A[]%2C%22enumCols%22%3A[]%2C%22return_remainder%22%3Afalse%2C%22should_pivot%22%3Afalse%2C%22is_timeseries%22%3Afalse%2C%22hideEmptyColumns%22%3Afalse%2C%22start%22%3A%22-1%20day%22%2C%22end%22%3A%22now%22%2C%22timezone%22%3A%22Europe%2FLondon%22%2C%22compare%22%3A[]%2C%22minBucketSamples%22%3A%22%22%2C%22samplingRatio%22%3A%221%22%2C%22dimensions%22%3A[%22dprefix%22]%2C%22metric%22%3A%22sumratemin%22%2C%22top%22%3A%2220%22%2C%22axes%22%3A%22linked%22%2C%22time_bucket%22%3A%22fine%22%2C%22smoothing_bucket%22%3A%221%22%2C%22scale_type%22%3A%22absolute%22%2C%22compare_mode%22%3A%22normal%22%2C%22overlay_types%22%3A[]%2C%22markers%22%3A%22%22%2C%22custom_title%22%3A%22%22%2C%22area%22%3A%22normal%22%2C%22aggregateList%22%3A[]%2C%22param_dimensions%22%3A[%7B%22dim%22%3A%22dthruas_ord%22%2C%22op%22%3A%22all%22%2C%22param%22%3A%221%22%2C%22anchor%22%3A%220%22%7D]%2C%22modifiers%22%3A[]%2C%22order%22%3A%22bps%22%2C%22order_desc%22%3Atrue%2C%22filterMode%22%3A%22DEFAULT%22%2C%22constraints%22%3A[[%7B%22column%22%3A%22scluster%22%2C%22op%22%3A%22eq%22%2C%22value%22%3A[%22[%5C%22{site}.{cluster}%5C%22]%22]%7D%2C%7B%22column%22%3A%22type_new%22%2C%22op%22%3A%22eq%22%2C%22value%22%3A[%22[%5C%22fna_egress_to_user%5C%22]%22]%7D]]%2C%22c_constraints%22%3A[[]]%2C%22b_constraints%22%3A[[]]%7D&normalized=1660728222&do_not_redirect=1".format(
        cluster=cluster_site, site=cluster_num
    )

    # Prefixes served from where?
    url6 = "https://www.internalfb.com/intern/scuba/query/?dataset=netflow&pool=uber&view=Area&drillstate=%7B%22purposes%22%3A[]%2C%22end%22%3A%22now%22%2C%22start%22%3A%22-1%20day%22%2C%22filterMode%22%3A%22DEFAULT%22%2C%22modifiers%22%3A[]%2C%22sampleCols%22%3A[]%2C%22cols%22%3A[%22bps%22]%2C%22derivedCols%22%3A[]%2C%22mappedCols%22%3A[]%2C%22enumCols%22%3A[]%2C%22return_remainder%22%3Afalse%2C%22should_pivot%22%3Afalse%2C%22is_timeseries%22%3Afalse%2C%22hideEmptyColumns%22%3Afalse%2C%22timezone%22%3A%22America%2FLos_Angeles%22%2C%22compare%22%3A[]%2C%22minBucketSamples%22%3A%22%22%2C%22samplingRatio%22%3A%221%22%2C%22dimensions%22%3A[%22outiface%22]%2C%22metric%22%3A%22sumratemin%22%2C%22top%22%3A%2250%22%2C%22axes%22%3A%22linked%22%2C%22time_bucket%22%3A%22auto%22%2C%22smoothing_bucket%22%3A%221%22%2C%22scale_type%22%3A%22absolute%22%2C%22compare_mode%22%3A%22normal%22%2C%22overlay_types%22%3A[]%2C%22markers%22%3A%22%22%2C%22custom_title%22%3A%22%22%2C%22area%22%3A%22normal%22%2C%22aggregateList%22%3A[]%2C%22param_dimensions%22%3A[%7B%22dim%22%3A%22dthruas_ord%22%2C%22op%22%3A%22all%22%2C%22param%22%3A%220%22%2C%22anchor%22%3A%220%22%7D]%2C%22order%22%3A%22bps%22%2C%22order_desc%22%3Atrue%2C%22constraints%22%3A[[%7B%22column%22%3A%22dprefix%22%2C%22op%22%3A%22eq%22%2C%22value%22%3A[%22[%5C%22163.47.157.0%2F24%5C%22]%22]%7D]]%2C%22c_constraints%22%3A[[]]%2C%22b_constraints%22%3A[[]]%2C%22ignoreGroupByInComparison%22%3Afalse%7D&normalized=1697624398&do_not_redirect=1"

    # Cluster served from POP
    url7 = "https://www.internalfb.com/intern/scuba/query/?dataset=netflow&pool=uber&view=Area&drillstate=%7B%22purposes%22%3A[]%2C%22cols%22%3A[%22bps%22]%2C%22derivedCols%22%3A[]%2C%22mappedCols%22%3A[]%2C%22enumCols%22%3A[]%2C%22return_remainder%22%3Afalse%2C%22should_pivot%22%3Afalse%2C%22is_timeseries%22%3Afalse%2C%22hideEmptyColumns%22%3Afalse%2C%22start%22%3A%22-1%20day%22%2C%22end%22%3A%22now%22%2C%22timezone%22%3A%22Europe%5C%2FLondon%22%2C%22compare%22%3A[]%2C%22minBucketSamples%22%3A%22%22%2C%22samplingRatio%22%3A%221%22%2C%22dimensions%22%3A[%22emetro%22%2C%22outiface%22]%2C%22metric%22%3A%22sumratemin%22%2C%22top%22%3A%2220%22%2C%22axes%22%3A%22linked%22%2C%22time_bucket%22%3A%22fine%22%2C%22smoothing_bucket%22%3A%221%22%2C%22scale_type%22%3A%22absolute%22%2C%22compare_mode%22%3A%22normal%22%2C%22overlay_types%22%3A[]%2C%22markers%22%3A%22%22%2C%22custom_title%22%3A%22%22%2C%22area%22%3A%22normal%22%2C%22aggregateList%22%3A[]%2C%22param_dimensions%22%3A[%7B%22dim%22%3A%22dthruas_ord%22%2C%22op%22%3A%22all%22%2C%22param%22%3A%221%22%2C%22anchor%22%3A%220%22%7D]%2C%22modifiers%22%3A[]%2C%22order%22%3A%22bps%22%2C%22order_desc%22%3Atrue%2C%22filterMode%22%3A%22DEFAULT%22%2C%22constraints%22%3A[[%7B%22column%22%3A%22dcluster%22%2C%22op%22%3A%22eq%22%2C%22value%22%3A[%22[%5C%22{site}.{cluster}%5C%22]%22]%7D%2C%7B%22column%22%3A%22type_new%22%2C%22op%22%3A%22eq%22%2C%22value%22%3A[%22[%5C%22pop_cache_fill%5C%22]%22]%7D]]%2C%22c_constraints%22%3A[[]]%2C%22b_constraints%22%3A[[]]%7D&normalized=1655300351&do_not_redirect=1".format(
        cluster=cluster_site, site=cluster_num
    )

    return (
        wb.open(url),
        wb.open(url2),
        wb.open(url3),
        wb.open(url4),
        wb.open(url5),
        wb.open(url6),
        wb.open(url7),
    )
    # return wb.open(urlnew)


def cluster_function(cluster):
    cluster, datacenter, cluster_num, cluster_number, cluster_standard = cluster_name(
        cluster
    )
    print(text.green("\nCluster: {}\n".format(cluster_standard)))
    (
        asn,
        isp,
        country_code,
        region,
        esm,
        ndm,
        recommendation,
        isp_address,
        isp_city,
        isp_state,
    ) = cluster_infos(cluster)
    isp_country = cluster_country(country_code)
    ipv4_peer, ipv6_peer, ipv4_prefix, ipv6_prefix = cluster_ips(
        datacenter, cluster_num
    )
    esm, ndm = get_full_name(esm), get_full_name(ndm)
    pop, as_path = scuba_emetro(cluster_number, datacenter)
    cgnat = cluster_cgnat(cluster_standard)
    cgnat_config = "Configured" if type(cgnat) is tuple else "Not Configured"
    cluster_testing(cluster, cluster_number, datacenter)
    cluster_info_print(
        cluster,
        asn,
        isp,
        ipv4_prefix,
        ipv6_prefix,
        ipv4_peer,
        ipv6_peer,
        pop,
        as_path,
        region,
        isp_country,
        isp_address,
        isp_city,
        isp_state,
        cgnat_config,
        esm,
        ndm,
        recommendation,
    )
    cluster_links(cluster)

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
    print(
        text.blue(f"\n {noc_input} It's a Local IP\n")
    ) if noc_input in local_ip else print(
        text.blue(f"\n {noc_input} It's a Remote IP\n")
    )
    return pr_aes, local_ip, remote_ip, asn, isp


# =============================== Interface Functions =============================== #

# Gets interfaces from a given PR_AE
def metroid_links_from_aes(pr_aes):
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
    int_tshoot(pr_ets)

    for link in links_print:
        print(text.dblue(link))
        wb.open(link)
    print()
    return links_print


# Runs commands on all interfaces of a given PR_AE
def int_tshoot(pr_ets):
    for pr_ae in pr_ets.keys():
        print(text.dred(f"\nTroubleshooting -- {pr_ae} --\n"))
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
                print(text.underline(f"{pr}:{intf} {printing[idx]}"))
                os.system("ssh {pr} '{c}'".format(pr=pr, c=command))

                idx += 1
                print("\n")

    # =============================== ASN Functions =============================== #


# Get country from ASN info
def isp_country(asn):
    name, country_code = asn_info(asn)
    print(name)
    isp_country = asn_country(country_code)
    return isp_country
