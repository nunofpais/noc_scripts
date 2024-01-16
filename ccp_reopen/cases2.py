# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import datetime
import os
import time

from datetime import date, timedelta
from typing import Optional

from analytics.bamboo import Bamboo as bb
from ens.noc_email.noc_to_ds.noc.ttypes import GenInternalNoteOnSupportTicket
from ens.noc_email.noc_to_ds.noc_ds_executer import (
    addInternalNoteToDSTicket,
    # createDSTicket,
    # createExternalCase,
    getDSTicketStatus,
    # getExternalCaseStatus,
    # passDSattachmentIDs,
)
from termcolor import cprint

# from ens.noc_email.noc_to_ds.noc_ds_executer import getDSTicketStatus

# from scripts.nunopais.test3.test3 import text

# Defining variables for following functions
timenow = int(time.time())
timepast = timenow - 172800  # 48 hours ago

# 24 hours ago converting PDT to UTC (UTC is 8 hour ahead of PDT)
hours24 = timenow - 115200

timenow_iso = str(datetime.datetime.fromtimestamp(timenow).isoformat())
timenow = timenow_iso.replace("T", "+")
timepast_iso = str(datetime.datetime.fromtimestamp(timepast).isoformat())
timepast = timepast_iso.replace("T", "+")
today_tmp = date.today() + timedelta(days=1)
today = str(today_tmp)
yesterday_tmp = today_tmp - timedelta(days=2)
yesterday = str(yesterday_tmp)
date_for_scuba = date.today()
date_for_scuba2 = date.today() - timedelta(days=60)


def is_sandcastle() -> bool:
    return os.getenv("SANDCASTLE") == "1" or os.getenv("TW_JOB_USER") == "sandcastle"


def get_presto_user() -> Optional[str]:
    user = "svc:chronos_secgrp_ens" if is_sandcastle() else None
    return user


def get_cases_24hrs():

    cases_df = bb.query_presto(
        sql=rf"""
        SELECT
            "fbid",
            "owner_id",
            "status_id",
            "vertical"
        FROM "fbobject_fbtype_2139_hourly_new"
        WHERE
            "ds" < '{today}'
            -- AND '{yesterday}' <= "ds"
            AND "ts" BETWEEN '{timepast}' AND '{timenow}'
            AND ("status_id") IN (1409779025921230)
            AND (
                STRPOS(LOWER("internal_tag_ids"), '273545239333342') >= 1
                OR STRPOS(LOWER("internal_tag_ids"), '732207593462310') >= 1
                OR STRPOS(LOWER("internal_tag_ids"), '44858124900') >= 1
                OR STRPOS(LOWER("internal_tag_ids"), '14677099419') >= 1
            )
            AND NOT ("case_type_id") IN (1089716978193872)
            AND NOT ("case_type_id") IN (491738614674537)
            AND ("vertical") IN ('npp')
        LIMIT
            1000
        """,
        namespace="operations",
        user=get_presto_user(),
    )

    cases_df = cases_df.drop_duplicates(subset=["fbid"], keep="first")
    # print(cases_df.tail(25))
    ui_cases = cases_df["fbid"].tolist()
    return cases_df, ui_cases


def get_comments_from_cases_UI(case):
    ########## Internal Comments ###########
    cprint(f"QUERYING INTERNAL COMMENTS FOR CASE ID: {case}", "green")
    ic = bb.query_presto(
        sql=rf"""
        SELECT
            "ds",
            "ts",
            "comment",
            "created",
            "external_case_id",
            "fbid",
            "mentioned_entities",
            "mtime"
        FROM "fbobject_fbtype_15190_hourly"
        WHERE
            '{yesterday}' <= "ds"
            AND "ds" < '{today}'
            AND "ts" BETWEEN '{timepast}' AND '{timenow}'
            AND (("external_case_id") IN ('{case}'))
        LIMIT
            100
        """,
        namespace="operations",
        user=get_presto_user(),
    )

    ic.head()
    ic = ic.drop_duplicates(subset=["created"])
    internal_comments = ic["comment"].tolist()
    # print("internal: ", internal_comments)
    internal_comments_string = " ".join(internal_comments)
    internal_comments = internal_comments_string.lower()

    ########## End of Internal Comments ##########

    ########## External Comments ##########
    cprint(f"QUERYING EXTERNAL COMMENTS FOR CASE ID: {case}", "green")
    ec = bb.query_presto(
        sql=rf"""
            WITH hr AS (
                SELECT
                    personal_fbid,
                    unix_username
                FROM
                    d_employee:hr
                WHERE
                    ds = '<LATEST_DS:d_employee:hr>'

            ), mapper AS (
                SELECT
                    *
                FROM
                    inc_dim_external_case_to_external_case_update_hourly:di
                WHERE
                    ds = '<LATEST_DS/LATEST_TS:inc_dim_external_case_to_external_case_update_hourly:di>'
                    AND ts = '<LATEST_TS/LATEST_DS:inc_dim_external_case_to_external_case_update_hourly:di>'

            ), mod AS (
                SELECT
                    *
                FROM
                    fbobject_fbtype_2111_hourly:di
                WHERE
                    ds = '<LATEST_DS/LATEST_TS:fbobject_fbtype_2111_hourly:di>'
                    AND ts = '<LATEST_TS/LATEST_DS:fbobject_fbtype_2111_hourly:di>'


            )
                SELECT
                    main.fbid                                   AS case_id,--1
                    CAST(main.createtime AS timestamp)          AS created_time,--2
                    -- owner_id                                    AS owner_fbid,--5
                    main.vertical                               AS system,--10
                    main.title                                  AS subject,--13
                    -- main.*,
                    mod.message as comment,
                    MIN(FROM_UNIXTIME(CAST(mod.created_time AS BIGINT))) as comment_time

                FROM fbobject_fbtype_2139_hourly_new:operations main
                LEFT JOIN mapper
                    ON main.fbid = mapper.id1
                LEFT JOIN mod
                    ON CAST(mod.fbid AS bigint) = mapper.id2
                WHERE CAST(main.createtime AS timestamp) > CAST('{date_for_scuba2}' AS TIMESTAMP)
                AND main.fbid = {case}
                GROUP BY 1,2,3,4,5
                ORDER BY 1,6
        """,
        namespace="infrastructure",
        user=get_presto_user(),
        ds=date_for_scuba,
    )
    ec.head()
    external_comments = ec["comment"].tolist()
    titles = ec["subject"].tolist()
    title = list(dict.fromkeys(titles))
    try:
        external_comments_string = "".join(external_comments)
        title_string = "".join(title)
    except TypeError:
        print("Something is wrong with external comments or the title")
    external_comments = external_comments_string.lower()
    title = title_string.lower()
    external_comments = external_comments + title

    ########## End of External comments ##########

    return internal_comments, external_comments


def add_internal_note(case, update):
    status = getDSTicketStatus(case)
    note_info = GenInternalNoteOnSupportTicket(
        ds_ticket_id=case,
        comment=update,
        status=status,
    )
    try:
        addInternalNoteToDSTicket(note_info)
    except Exception as ex:
        print(ex)


# print("nwt_matches", nwt_matches)
# print("nwts_closed", nwts_closed)
# print("nwt_followup_24h", nwt_followup_24h)
# print("nwt_comment_24h", nwt_comment_24h)
# print("tasks_matches", task_matches)
# print("tasks_closed", tasks_closed)
# print("sev_matches", sev_matches)
# print("sevs_closed", sevs_closed)
# print("workplace_esc", workplace_esc)
# suggestions = []

# def case_reopened_internal_comment(case, )
# if len(nwts_closed) > 0 or len (nwt_followup_24h) > 0 or len(nwt_comment_24h) > 0:
#     print("NWTs comment")
#     print("NWTs followup")
#     print("NWTs closed")

# if len(nwt_matches) > 0:
