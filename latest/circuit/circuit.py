# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
import sys

from libfb.py.thrift_clients.skynet_thrift_client import SkynetThriftClient
from nettools.skynet.Query.ttypes import Expr, Op, Query as SkynetQuery


class text:
    """
    Text formatting for cli output
    """

    DGREEN = "\033[38;5;34m"
    RED = "\033[38;5;196m"
    DRED = "\033[38;5;124m"
    DBLUE = "\033[38;5;21m"
    END = "\033[0;0m"

    def dgreen(self: str) -> str:
        return f"{text.DGREEN}{self}{text.END}"

    def red(self: str) -> str:
        return f"{text.RED}{self}{text.END}"

    def dred(self: str) -> str:
        return f"{text.DRED}{self}{text.END}"

    def dblue(self: str) -> str:
        return f"{text.DBLUE}{self}{text.END}"


# Get input (eg: circuit FC-7672361)
if len(sys.argv) == 2:
    efs_input = sys.argv[1]  # FC-7672361
else:
    efs_input = ""
    print(
        text.red(
            "Please provide an input (IP, cluster, peering router port, circuit ID)"
        )
    )

efs_input = efs_input.lower()


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


# checks status (up/down and light levels) for LAG interfaces
def int_tshoot(pr, interfaces):
    commands = []
    printing = ["OPTICS", "STATS"]
    printing = printing * len(interfaces)
    for intf in interfaces:
        sintax = 'show interfaces {i} statistics | grep "Physical|Description|Link-level|Last|Input|Output"'.format(
            i=intf
        )
        sintax2 = (
            "show interfaces diagnostics optics {i} | match dbm | except thre".format(
                i=intf
            )
        )
        commands.append(sintax2)
        commands.append(sintax)
    idx = 0
    for command in commands:
        print("\n\nInterface {i} {p} \n".format(i=intf, p=printing[idx]))
        os.system("ssh {pr} '{c}'".format(pr=pr, c=command))
        # os.system("cat interface.txt")
        idx += 1
        print("\n")


# Main Circuit Function
def circuit_function(circuit_id):
    circuit = circuit_finder(circuit_id)
    pr, agg_intf, et_intf = (
        circuit["pr_ae"].split(":")[0],
        circuit["ae"],
        [circuit["et"]],
    )
    print(text.dgreen("\n\n-- {c} --").format(c=circuit["pr_ae"]))
    print(
        "\n\nCircuit Device: {pr}\nPort-channel: {agg}\nCircuit Interface: {et}\n".format(
            pr=pr, agg=agg_intf, et=et_intf
        )
    )
    int_tshoot(pr, et_intf)
    print(
        text.dblue(
            "https://www.internalfb.com/intern/bunny/?q=%s"
            % "metroid+{}".format(circuit["pr_ae"])
        )
    )
    print(
        text.dblue(
            "https://www.internalfb.com/intern/bunny/?q=%s"
            % "metroid+{}:{}\n".format(pr, et_intf[0])
        )
    )


circuit = circuit_function(efs_input)
