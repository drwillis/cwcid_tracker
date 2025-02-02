import argparse
from datetime import datetime, timedelta
from cwcid_git_commit_analysis import track_git_changes, send_email

if __name__ == "__main__":
    from cwcid_default_auth_credentials import email_auth_dict,  overleaf_auth_dict
    from cwcid_default_repository_data import repo_dict_data

    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description='A script to monitor git repository changes and notify contributors.')

    # Add arguments
    parser.add_argument('-n', '--notify', action='store_true',
                        help='Send report notifications to contributors via email')
    # Parse the arguments
    args = parser.parse_args()

    notify = args.notify

    # Get the current date
    now = datetime.now()

    day_start = now - timedelta(days=1)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    year_start = now - timedelta(days=365)
    time_interval_dicts = [
        {
            "Time Start": day_start,
            "Period": "Daily"
        }, {
            "Time Start": week_start,
            "Period": "Weekly"
        }, {
            "Time Start": month_start,
            "Period": "Monthly"
        }, {
            "Time Start": year_start,
            "Period": "Yearly"
        }
    ]
    global_author_notification = {}
    for collaborative_data_target in repo_dict_data:
        one_element_repo_dict_data = [collaborative_data_target]
        item_author_notifications = track_git_changes(one_element_repo_dict_data, overleaf_auth_dict, time_interval_dicts)
        global_author_notification.update(item_author_notifications)

    if args.notify:
        for notify_email in global_author_notification.keys():
            # Send the statistics via email
            email_body = global_author_notification[notify_email]["body"]
            # Remove duplicates using set
            if "CC" in global_author_notification[notify_email]:
                CC_list = list(set(global_author_notification[notify_email]["CC"]))
            else:
                CC_list = []
            if "Reply-to" in global_author_notification[notify_email]:
                reply_to = global_author_notification[notify_email]["Reply-to"]
            else:
                reply_to = None
            print(f"Sending email to {notify_email} and CC: {CC_list} with Reply-to: {reply_to}")
            email_routing_dict = {"TO": [notify_email], "CC": CC_list, "Reply-to": reply_to}
            now_datestr = now.strftime("%Y-%m-%d")
            email_subject = f"Daily Code and Writing Productivity Report for {now_datestr}"
            send_email(email_subject, email_body, email_routing_dict, email_auth_dict)