# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
import time
from datetime import date, timedelta
from typing import Optional

from analytics.bamboo import Bamboo as bb
from libfb.py.thrift import CLIENT_ID
from nettools.skynet.Query.ttypes import Expr, Op, Query
from nettools.skynet.Skynet import Skynet
from servicerouter.srproxy import ClientParams, get_sr_client

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


def cluster_peer_ip(mna_input):
    cluster_peer_ip = bb.query_mysql(
        f"""
    SELECT datacenter, cluster_number
    FROM clusters
    WHERE ipv4_bgp_neighbors = '{mna_input}'
    """,
        "xdb.fna",
    )
    if cluster_peer_ip.empty:
        cluster = ""
    else:
        cluster_values = cluster_peer_ip.values.tolist()[0]
        cluster = cluster_values[0] + "-" + cluster_values[1]
    return cluster


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
