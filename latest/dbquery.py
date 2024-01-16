# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
import sys
import time
from datetime import date, timedelta
from typing import Optional

from analytics.bamboo import Bamboo as bb
from libfb.py.thrift import CLIENT_ID
from libfb.py.thrift_clients.skynet_thrift_client import SkynetThriftClient
from nettools.skynet.Query.ttypes import Expr, Op, Query, Query as SkynetQuery
from nettools.skynet.Skynet import Skynet
from servicerouter.srproxy import ClientParams, get_sr_client


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

    # =============================== Circuit Queries =============================== #


# Get all infos from a Circuit ID
def circuit_finder(circuit_id):
    # circuit_id = "FC-7923259"
    with SkynetThriftClient() as skynet:
        query = SkynetQuery(
            exprs=[
                Expr(
                    name="vendor_circuit_id",
                    op=Op.EQUAL,
                    values=[circuit_id],
                )
            ]
        )
        fields = [
            "vendor_circuit_id",
            "a_endpoint.display_name",
            "a_endpoint.name",
            "a_endpoint.aggregated_interface.display_name",
            "a_endpoint.aggregated_interface.name",
            "vendor.peer.as_no",
            "vendor.description",
        ]
        res = skynet.getDesiredCircuit(query, fields)

    # skycli_json = [device.a_endpoint.display_name for port in res]
    circuit = []
    for circuit_info in res:
        circuit.append(
            {
                "id": circuit_info.vendor_circuit_id,
                "pr_et": circuit_info.a_endpoint.display_name,
                "et": circuit_info.a_endpoint.name,
                "pr_ae": circuit_info.a_endpoint.aggregated_interface.display_name,
                "ae": circuit_info.a_endpoint.aggregated_interface.name,
                "asn": circuit_info.vendor.peer.as_no,
                "isp": circuit_info.vendor.description,
            }
        )

    sys.exit(text.red("\nCircuit ID NOT FOUND\n")) if not circuit else circuit
    circuit = circuit[0]

    if "rsw1aa" in circuit["pr_et"]:
        cluster = circuit["pr_et"].split(":")[0]
        cluster = cluster.split(".", 1)[1]
        cluster_num, datacenter = cluster.split(".")
        cluster_number = [cluster_num[-1] if cluster_num[-2] == "0" else cluster_num][0]
        cluster = datacenter + "-" + cluster_number
        print(
            text.red(
                "This circuit belongs to cluster {}\nExiting".format(cluster.upper())
            )
        )
        exit()

    return circuit

    # =============================== Cluster Queries =============================== #


# Get general info from cluster
def cluster_infos(cluster):
    cluster_bbe = bb.query_mysql(
        f"""
        SELECT asn, isp, country, region, esm, ndm, recommendation, physical_address, physical_city, physical_state_province
        FROM edge_clusters
        WHERE cluster_id = '{cluster}'
        """,
        "xdb.bbe_snap",
    )
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
    ) = cluster_bbe.values.tolist()[0]
    return (
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
    )


# Get country name from country code
def cluster_country(country_code):
    cluster_bbe2 = bb.query_mysql(
        f"""
        SELECT country
        FROM country_approval_status
        WHERE country_code = '{country_code}'
        """,
        "xdb.bbe_snap",
    )
    country = cluster_bbe2.values.tolist()[0][0]
    return country


# Get IP info from cluster
def cluster_ips(datacenter, cluster_num):
    cluster_fna = bb.query_mysql(
        f"""
        SELECT ipv4_bgp_neighbors, ipv6_bgp_neighbors, ipv4_prefix, ipv6_prefix
        FROM clusters
        WHERE datacenter = '{datacenter}'
        AND cluster_number = '{cluster_num}'
        """,
        "xdb.fna",
    )
    ipv4_peer, ipv6_peer, ipv4_prefix, ipv6_prefix = " ", " ", " ", " "
    ip_list = cluster_fna.values.tolist()[0]
    ip_list = ["N/A" if v is None or v == "" else v for v in ip_list]
    ipv4_peer, ipv6_peer, ipv4_prefix, ipv6_prefix = ip_list
    return ipv4_peer, ipv6_peer, ipv4_prefix, ipv6_prefix


def cluster_peer_ip(noc_input):
    cluster_peer_ip = bb.query_mysql(
        f"""
    SELECT datacenter, cluster_number
    FROM clusters
    WHERE ipv4_bgp_neighbors = '{noc_input}'
    """,
        "xdb.fna",
    )
    if cluster_peer_ip.empty:
        cluster = ""
    else:
        cluster_values = cluster_peer_ip.values.tolist()[0]
        cluster = cluster_values[0] + "-" + cluster_values[1]
    return cluster


# Get CGNAT info from cluster
def cluster_cgnat(cluster_standard):
    cluster_bbe = bb.query_mysql(
        f"""
        SELECT cluster_id, ds, violation_message, route_info
        FROM cgnat_violation_records
        WHERE cluster_id = '{cluster_standard}'
        ORDER BY ID DESC LIMIT 1
        """,
        "xdb.bbe_snap",
    )
    cluster_id, date, cgnat_error, cgnat_info = cluster_bbe.values.tolist()[0]
    return (
        (date, cgnat_error, cgnat_info)
        if cgnat_info != "not configured"
        else cgnat_info
    )


# Get POP location and AS Path
def scuba_emetro(cluster_number, datacenter):

    timenow_timestamp = int(time.time())
    time24h_timestamp = timenow_timestamp - 86400
    tomorrow_date = str(date.today() + timedelta(days=1))
    # today_date = str(date.today)
    yesterday_date = str(date.today() - timedelta(days=1))

    scuba_cluster = cluster_number + "." + datacenter

    def is_sandcastle() -> bool:
        return (
            os.getenv("SANDCASTLE") == "1" or os.getenv("TW_JOB_USER") == "sandcastle"
        )

    def get_presto_user() -> Optional[str]:
        user = "svc:chronos_secgrp_ens" if is_sandcastle() else None
        return user

    df = bb.query_presto(
        sql=rf"""
        SELECT
            SUM("weight") as "weight",
            COUNT(1) as "weight_int", SUM(("bps") * "weight") as "agg::1",
            CAST (("time" - 1684400836) AS BIGINT) / 240 * 240 + 1684400836 as "timestamp", "emetro",
            REVERSE("dthruas_ord") as "AS Path"
        FROM
          "netflow"
        WHERE
          '{yesterday_date}' <= "ds" AND "ds" < '{tomorrow_date}'
          AND "time" BETWEEN {time24h_timestamp} AND {timenow_timestamp}
          AND (("dcluster") IN ('{scuba_cluster}'))
          AND ("dthruas" IS NOT NULL AND CARDINALITY("dthruas") > 0)
        GROUP BY
          4,5,6
        HAVING
          Count(1) > 0
        ORDER BY
          "agg::1" DESC
        LIMIT
          86400
        """,
        namespace="infrastructure",
        user=get_presto_user(),
    )

    df.head()
    pop_result = df.drop_duplicates(subset=["emetro"])
    pop_result = pop_result.iloc[0].tolist()
    pop, as_path = pop_result[-2], pop_result[-1]

    return pop, as_path


# Get cluster name from ip
def cluster_peer(ip, cluster_prefix):
    ip = ip + "%"
    cluster_bbe2 = bb.query_mysql(
        f"""
        SELECT datacenter, cluster_number
        FROM clusters
        WHERE ipv4_prefix = '{cluster_prefix}'
        OR ipv4_p2p_uplink LIKE '{ip}'
        OR ipv4_p2p_local LIKE '{ip}'
        """,
        "xdb.fna",
    )
    cluster = cluster_bbe2.values.tolist()
    return cluster

    # =============================== IPTool Queries =============================== #


# Parent IP Data
def get_parent_data(efs_input):
    params = ClientParams().setClientId(CLIENT_ID)
    with get_sr_client(Skynet.Client, "skynet_thrift", params=params) as skynet:
        fields = [
            "description",
            "id",
            "prefix",
            "prefix_length",
            "children.derived_type",
            "children.description",
            "children.id",
            "children.prefix",
            "children.pniv4prefix.as_no",
        ]
        query = Query(
            exprs=[
                Expr(name="children.prefix", op=Op.EQUAL, values=[efs_input]),
            ]
        )

        return skynet.getDesiredV4Prefix(query, fields)


# Children IP Data
def get_children_data(parent_id):
    params = ClientParams().setClientId(CLIENT_ID)
    with get_sr_client(Skynet.Client, "skynet_thrift", params=params) as skynet:
        fields = [
            "id",
            "prefix",
            "prefix_length",
            "children.derived_type",
            "children.description",
            "children.id",
            "children.prefix",
            "children.pniv4prefix.as_no",
        ]
        query = Query(exprs=[Expr(name="id", op=Op.EQUAL, values=[parent_id])])

        return skynet.getDesiredV4Prefix(query, fields)


# Interfaces Data
def get_interfaces_data(pr_ae):
    params = ClientParams().setClientId(CLIENT_ID)
    with get_sr_client(Skynet.Client, "skynet_thrift", params=params) as skynet:
        fields = [
            "display_name",
            "aggregatedinterface.display_name",
            "aggregatedinterface.physicalinterfaces.name",
        ]
        query = Query(exprs=[Expr(name="display_name", op=Op.EQUAL, values=[pr_ae])])

        return skynet.getDerivedInterface(query, fields)

    # =============================== Peering Queries =============================== #


# Get country name from country code
def asn_country(country_code):
    cluster_bbe2 = bb.query_mysql(
        f"""
        SELECT country
        FROM country_approval_status
        WHERE country_code = '{country_code}'
        """,
        "xdb.bbe_snap",
    )
    country = cluster_bbe2.values.tolist()[0][0]
    return country


# Get infos from asn
def asn_info(asn):
    cluster_bbe2 = bb.query_mysql(
        f"""
        SELECT name, primary_country
        FROM asns
        WHERE asn = '{asn}'
        """,
        "xdb.bbe_snap",
    )
    name, country_code = cluster_bbe2.values.tolist()[0]
    return name, country_code


def remote_ip_bgp_session(remote_ip):
    params = ClientParams().setClientId(CLIENT_ID)
    with get_sr_client(Skynet.Client, "skynet_thrift", params=params) as skynet:
        fields = ["ip", "peer.as_no", "local_prefix.description", "peer.name"]
        query = Query(exprs=[Expr(name="ip", op=Op.EQUAL, values=[remote_ip])])

        return skynet.getDesiredBgpV4Session(query, fields)
