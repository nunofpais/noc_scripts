# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

from analytics.bamboo import Bamboo as bb

from libfb.py.thrift import CLIENT_ID
from nettools.skynet.Query.ttypes import Expr, Op, Query
from nettools.skynet.Skynet import Skynet
from servicerouter.srproxy import ClientParams, get_sr_client


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
