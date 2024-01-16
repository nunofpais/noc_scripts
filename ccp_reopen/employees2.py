# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
from datetime import date, timedelta

from typing import Optional

from analytics.bamboo import Bamboo as bb

from libfb.py.employee import get_full_name


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


# =============== Query Variables Definition ===============#


# timenow_temp = int(time.time())
# timenow_iso = str(datetime.datetime.fromtimestamp(timenow_temp).isoformat())
# timenow = timenow_iso.replace("T", "+")
# timepast_temp = timenow_temp - 172800  # 48 hours ago
# timepast_iso = str(datetime.datetime.fromtimestamp(timepast_temp).isoformat())
# timepast = timepast_iso.replace("T", "+")
# today_tmp = date.today() + timedelta(days=1)
# today = str(today_tmp)
# yesterday_tmp = today_tmp - timedelta(days=2)
# yesterday = str(yesterday_tmp)
# dby = today_tmp - timedelta(days=3)
# # print(dby)
# date_for_scuba = date.today()
# date_for_scuba2 = date.today() - timedelta(days=60)
# service_user = 89002005298961

today = date.today() + timedelta(days=1)
yesterday = today - timedelta(days=2)
today = str(today)
yesterday = str(yesterday)


def is_sandcastle() -> bool:
    return os.getenv("SANDCASTLE") == "1" or os.getenv("TW_JOB_USER") == "sandcastle"


def get_presto_user() -> Optional[str]:
    user = "svc:chronos_secgrp_ens" if is_sandcastle() else None
    return user


# =============== Get ESM NDM ICMS ===============#


def get_managers_list():
    def get_esm_data():
        esm = bb.query_mysql(
            """
            SELECT lead_id
            FROM country_approval_status
            """,
            "xdb.fna",
        )

        esm.drop_duplicates(subset=["lead_id"])
        esm_result = esm.drop_duplicates(subset=["lead_id"])
        esm_list = esm_result["lead_id"].tolist()
        # print(esm_list)
        # print(esm.drop_duplicates(subset=["lead_id"]))

        return esm_list

    def get_ndm_data():
        ndm = bb.query_mysql(
            """
            SELECT ndm_id
            FROM country_approval_status
            """,
            "xdb.fna",
        )

        ndm.drop_duplicates(subset=["ndm_id"])
        ndm_result = ndm.drop_duplicates(subset=["ndm_id"])
        ndm_result2 = ndm_result[ndm_result["ndm_id"].notnull()]
        # print(ndm_result2)
        ndm_list = ndm_result2["ndm_id"].tolist()

        return ndm_list

    def get_icms_data():
        icms = bb.query_presto(
            sql=rf"""
            SELECT
                "ds",
                "member_userids",
                "oncall_rotation_short_name"
            FROM "oncall_rotation_members"
            WHERE
                '{yesterday}' <= "ds"
                AND "ds" < '{today}'
                AND (STRPOS(LOWER("oncall_rotation_short_name"), 'icms') >= 1)
                AND NOT (STRPOS(LOWER("oncall_rotation_short_name"), 'tableau') >= 1)
            LIMIT
                100
            """,
            namespace="infrastructure",
            user=get_presto_user(),
        )

        icms.head()
        # print(icms)

        icms_list_temp = icms["member_userids"].tolist()
        icms_list = [item for sublist in icms_list_temp for item in sublist]
        # print(icms_list)

        return icms_list

    esm_list = get_esm_data()
    ndm_list = get_ndm_data()
    icms_list = get_icms_data()

    managers_list = []
    for a in esm_list:
        full_name = get_full_name(a)
        managers_list.append(full_name)

    for b in ndm_list:
        full_name = get_full_name(b)
        managers_list.append(full_name)

    for c in icms_list:
        full_name = get_full_name(c)
        managers_list.append(full_name)

    managers_list = [each_string.lower() for each_string in managers_list]
    # nwt_note_df(managers_list)

    return managers_list


# =============== End of ESM, NDM ===============#
