# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
from datetime import date, timedelta
from typing import Optional

from ens.noc_email.noc_to_ds.noc_ds_executer import addCommentToDSTicket

from scripts.nunopais.test2.cases2 import (
    add_internal_note,
    get_cases_24hrs,
    get_comments_from_cases_UI,
)
from scripts.nunopais.test2.tickets2 import (
    check_nwt_deprecation,
    nwt_info,
    sev_info,
    task_info,
    ticket_in_comments,
)
from termcolor import cprint


SMC_TIER = "noc_to_ds_thrift"
configs = {"processing_timeout": "300000"}


# ============== VARIABLE DEFINITION ===================== #

today_tmp = date.today() + timedelta(days=1)
today = str(today_tmp)
yesterday_tmp = today_tmp - timedelta(days=2)
yesterday = str(yesterday_tmp)


def is_sandcastle() -> bool:
    return os.getenv("SANDCASTLE") == "1" or os.getenv("TW_JOB_USER") == "sandcastle"


def get_presto_user() -> Optional[str]:
    user = "svc:chronos_secgrp_ens" if is_sandcastle() else None
    return user


# =================================  Get CASES ================================= #

# ui_cases = [1005277474065735]  # TEST CASE
cases_df, ui_cases = get_cases_24hrs()
cprint(f"NUMBER OF CASES: {len(ui_cases)}", "blue", attrs=["bold"])


# Get tickets' status
ticket_status = {
    0: "Closed",
    2: "Diagnosed",
    3: "Resolved",
    4: "Undiagnosed",
    6: "Blocked",
}

# =================================  Loop Through CASES ================================= #

cases_reopened = []
all_comments = []
final_comments = []

update_no_comments = """
Hi,\n
Our team is going to review your case and will get back to you shortly with the investigation result.\n
Regards\n
Meta Support
"""

for case in ui_cases:
    cprint(f"\n\nCASE ID: {case}", attrs=["bold"])

    # Getting comments from UI cases
    internal_comments, external_comments = get_comments_from_cases_UI(case)
    comments = internal_comments + external_comments

    # Find data in comments
    nwt_matches, task_matches, sev_matches, workplace_esc = ticket_in_comments(comments)

    if len(nwt_matches) == 0 and len(task_matches) == 0 and len(sev_matches) == 0:
        print(
            "No nwt or tasks or SEV or ESM escalations or Workpace escalations in the commments"
        )
    else:

        # Get status of nwt/tasks/sevs

        nwts_closed = []
        nwts_not_closed = []
        nwt_followup_24h = []
        nwt_comment_24h = []
        tasks_closed = []
        tasks_not_closed = []
        sevs_closed = []
        ticket_comments = []

        # ================================= NWT Section ================================= #

        # 1. Check if there are any NWTs
        nwt_comments = [f"\n*Case ID: {case}*"]
        ticket_comments.append(f"\n\n*Case ID: {case}*")
        ticket_comments.append(
            "This case has all attached tickets closed or not updated in 24 hours.\nKindly check if the issue still exists:\n- If yes, please update the case.\n- If no, please close the case."
        )

        if len(nwt_matches) > 0:
            cprint(f"NWTs on this case: {nwt_matches}", "blue")
            nwt_comments.append(
                "=== NWT(s) on this case: " + ", ".join(nwt_matches) + " ==="
            )
            ticket_comments.append(
                "\n=== NWT(s) on this case: " + ", ".join(nwt_matches) + " ==="
            )
            for n in nwt_matches:
                nwt_number = n[3:]
                # 1.1 Check ticket information and status
                nwt_df = nwt_info(nwt_number, ticket_status)
                nwt_last_modified = nwt_df["last_modified_time"][0]

                if nwt_df["status"][0] == 0 or nwt_df["status"][0] == 3:
                    nwts_closed.append(n)
                    nwt_status = ticket_status[nwt_df["status"][0]]
                    cprint(f"{n} is {nwt_status}", attrs=["bold"])

                else:
                    nwts_not_closed.append(n)
                    # 1.2 If ticket not closed, check if 24 hours passed since last modification
                    (
                        nwt_followup_24h,
                        nwt_comment_24h,
                        nwt_comments,
                        ticket_comments,
                    ) = check_nwt_deprecation(
                        n,
                        nwt_df,
                        nwt_last_modified,
                        nwt_followup_24h,
                        nwt_comment_24h,
                        nwt_comments,
                        ticket_comments,
                    )
            print("NWTS Closed: ", nwts_closed)
            print("NWTS not Closed: ", nwts_not_closed)
            if nwts_closed != []:
                nwt_comments.append("NWT(s) Closed: " + ", ".join(nwts_closed))
                ticket_comments.append("NWT(s) Closed: " + ", ".join(nwts_closed))

        # ================================= TASK Section ================================= #

        # 2. Check if there are any Tasks
        task_comments = []
        if len(task_matches) > 0:
            cprint(f"\nTasks on this case: {task_matches}", "blue")
            task_comments.append(
                "\n=== Task(s) on this case: " + ", ".join(task_matches) + " ==="
            )
            ticket_comments.append(
                "\n=== Task(s) on this case: " + ", ".join(task_matches) + " ==="
            )
            for t in task_matches:
                tasks_closed, tasks_not_closed = task_info(
                    t, tasks_closed, tasks_not_closed
                )
            tasks_closed_str = ", ".join(tasks_closed)
            task_comments.append("Task(s) Closed: " + tasks_closed_str)
            ticket_comments.append("Task(s) Closed: " + tasks_closed_str)
            print("Tasks closed: ", tasks_closed)
            print("Tasks not closed: ", tasks_not_closed)

        # ================================= SEV Section ================================= #

        # 3. Check if there are any SEVs
        sev_comments = []
        if len(sev_matches) > 0:
            cprint(f"\nSEVs on this case: {sev_matches}", "blue")
            sev_comments.append(
                "\n=== SEV(s) on this case: " + ", ".join(sev_matches) + " ==="
            )
            ticket_comments.append(
                "\n=== SEV(s) on this case: " + ", ".join(sev_matches) + " ==="
            )
            sevs_closed = []
            for s in sev_matches:
                sevs_closed = sev_info(s, yesterday, today, sevs_closed)
            sevs_closed_str = ", ".join(sevs_closed)
            sev_comments.append("SEV(s) Closed: " + sevs_closed_str)
            ticket_comments.append("SEV(s) Closed: " + sevs_closed_str)
            print("Total SEVs: ", sev_matches)
            print("SEVs closed: ", sevs_closed)

        # ================================= Reopen Cases ================================= #

        # 4. Check if case should be reopened if all tickets related are closed/not updated in 24 hours
        if (
            len(nwt_matches) == len(nwts_closed)
            or len(nwt_matches)
            == len(nwt_followup_24h) + len(nwt_comment_24h) + len(nwts_closed)
            and len(nwt_matches) > 0
        ):
            if len(tasks_closed) == len(task_matches) and len(sevs_closed) == len(
                sev_matches
            ):
                cprint(f"Hello: Should {case} be Closed?", "red")

                # Print all comments
                ticket_comments = """{}""".format("\n".join(ticket_comments))
                # print("ticket_comments", ticket_comments)
                final_comments.append(ticket_comments)
                update = ticket_comments
                print("Reopening the case with details")
                addCommentToDSTicket(
                    case, "EFSupdate@meta.com", update_no_comments, "REOPENED"
                )
                add_internal_note(case, update)
                cases_reopened.append(case)

if len(cases_reopened) > 0:
    cprint("\n\nCCP Cases Reopened REPORT", "green")
    cprint(f"\nCases Reopened: {cases_reopened}", "red")

all_comments = """{}""".format("\n".join(final_comments))
print("\n Internal Comments printed to all Reopened Cases", all_comments)
