# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
import re
import time
from subprocess import PIPE, run
from typing import Optional

from analytics.bamboo import Bamboo as bb
from termcolor import cprint

# =============== Query Variables Definition ===============#

# 24 hours ago converting PDT to UTC (UTC is 8 hour ahead of PDT)
hours24 = int(time.time()) - 115200


def is_sandcastle() -> bool:
    return os.getenv("SANDCASTLE") == "1" or os.getenv("TW_JOB_USER") == "sandcastle"


def get_presto_user() -> Optional[str]:
    user = "svc:chronos_secgrp_ens" if is_sandcastle() else None
    return user


# =============== Comments Section =============== #


def ticket_in_comments(comments):
    regex_nwt = r"nwt\d{1,}"
    regex_task = r"\b[Tt]\d{7,}"
    regex_sev = r"[Ss]\d{6,7}"
    regex_worplace_escalation = r"workplace.com"

    nwt_matches = re.findall(regex_nwt, comments, re.MULTILINE)
    nwt_matches = list(dict.fromkeys(nwt_matches))

    task_matches = re.findall(regex_task, comments, re.MULTILINE)
    task_matches = list(dict.fromkeys(task_matches))

    sev_matches = re.findall(regex_sev, comments, re.MULTILINE)
    sev_matches = list(dict.fromkeys(sev_matches))

    workplace_esc = re.findall(regex_worplace_escalation, comments, re.MULTILINE)
    workplace_esc = list(dict.fromkeys(workplace_esc))

    return nwt_matches, task_matches, sev_matches, workplace_esc


# =============== NWT Section =============== #


def nwt_info(nwt_number, ticket_status):
    nwt_df = bb.query_mysql(
        f"""
        SELECT status, ticket_id, ticket_number, last_modified_time
        FROM sort_ticket
        WHERE ticket_number = {nwt_number}
        """,
        "xdb.resort",
    )
    nwt_df.head()
    return nwt_df


def nwt_notes(nwt_df):
    # print(nwt_number)
    nwt_notes_df = bb.query_mysql(
        f"""
        SELECT comment, follow_up_date, last_modified_time
        FROM sort_escalation
        WHERE ticket_id = {nwt_df["ticket_id"][0]}
        ORDER BY last_modified_time DESC
        """,
        "xdb.resort",
    )
    nwt_notes_df.head()
    return nwt_notes_df


def check_nwt_deprecation(
    n,
    nwt_df,
    nwt_last_modified,
    nwt_followup_24h,
    nwt_comment_24h,
    nwt_comments,
    ticket_comments,
):
    # print(n, type (n))
    if not nwt_df.empty:
        nwt_notes_df = nwt_notes(nwt_df)
        # 1.2.1 If ticket has notes
        if not nwt_notes_df.empty:
            follow_up_date = nwt_notes_df["follow_up_date"].max()
            if follow_up_date < hours24:
                follow_up_date_time = time.ctime(follow_up_date)
                nwt_comments.append(
                    f"{n}: Follow Up Date is more than 24h --> {follow_up_date_time}"
                )
                ticket_comments.append(
                    f"{n}: Follow Up Date is more than 24h --> {follow_up_date_time}"
                )
                cprint(f"{n}: Follow Up Date is more than 24h --> {follow_up_date_time}", "red")
                # print(f"{n} was updated on ", time.ctime(nwt_last_modified))
                # print(f"adding {n} to nwt_more_24h")
                nwt_followup_24h.append(n)
            # else:
            #     print(
            #         text.dgreen(f"{n} is within the Follow Up Date\n")
            #     )

            # print("FOLLOW UP DATE: ", time.ctime(follow_up_date))

        else:
            if nwt_last_modified < hours24:
                last_comment_time = time.ctime(nwt_last_modified)
                nwt_comments.append(
                    f"{n}: Last Comment has more than 24h --> {last_comment_time}"
                )
                ticket_comments.append(
                    f"{n}: Last Comment has more than 24h --> {last_comment_time}"
                )
                nwt_comment_24h.append(n)
                cprint(f"{n} Last Comment is more than 24h", "red")

        return nwt_followup_24h, nwt_comment_24h, nwt_comments, ticket_comments


# =============== Task Section =============== #


def task_info(task_number, tasks_closed, tasks_not_closed):
    _command_taskscli = f"tasks summary {task_number} 2> /dev/null"
    result_command_taskscli = run(
        _command_taskscli, stdout=PIPE, encoding="utf8", shell=True
    )
    # 2.1 Check task information and status
    try:
        output_taskscli = result_command_taskscli.stdout.splitlines()
        # print(output_taskscli)
        task_values = re.sub(" +", " ", output_taskscli[0])
        task_values = task_values.split(" ", 4)
        task_idx = ["task_id", "owner", "status", "priority", "title"]
        task = dict(zip(task_idx, task_values))
        task_status = task["status"]
        cprint(f"{task_number} is {task_status}", attrs=["bold"])
        tasks_closed.append(task_number) if task[
            "status"
        ] == "CLOSED" else tasks_not_closed.append(task_number)
    except IndexError:
        print(f"You cannot access {task_number} at this time")

    return tasks_closed, tasks_not_closed


# =============== SEV Section =============== #


def sev_info(sev_number, yesterday, today, sevs_closed):
    sev_id = sev_number[1:]
    sev = bb.query_presto(
        sql=rf"""
        SELECT
            "event_status",
            "sev_number"
        FROM "dim_sev_events"
        WHERE
            '{yesterday}' <= "ds"
            AND "ds" < '{today}'
            AND (("sev_number") IN ({sev_id}))
        LIMIT
            1
        """,
        namespace="infrastructure",
        user=get_presto_user(),
    )
    sev.head()
    sev_status = sev["event_status"].tolist()
    if 250122605176193 or 466342750155866 in sev_status:
        sevs_closed.append(sev_number)

    return sevs_closed
