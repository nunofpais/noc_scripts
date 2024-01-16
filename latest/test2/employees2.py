# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
from datetime import date, timedelta

from typing import Optional

from analytics.bamboo import Bamboo as bb

from libfb.py.employee import get_full_name


# =============== Query Variables Definition ===============#

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
        icms_list_temp = icms["member_userids"].tolist()
        icms_list = [item for sublist in icms_list_temp for item in sublist]
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
    return managers_list


# =============== End of ESM, NDM ===============#
