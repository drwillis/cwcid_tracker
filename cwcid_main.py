import argparse
from datetime import datetime
from cwcid_git_commit_analysis import track_git_changes, plot_change_history, send_email

if __name__ == "__main__":
    from cwcid_default_auth_credentials import email_auth_dict, overleaf_auth_dict
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

    track_git_changes(repo_dict_data, overleaf_auth_dict)

    # collect statistics on each repository
    for repo_dict in repo_dict_data:
        print(repo_dict)
        if "stats" in repo_dict:
            repo_stats = repo_dict["stats"]
            plot_change_history(repo_dict)

    # print(repo_dict_data)
    author_notifications = {}
    email_body = "Report statistics are included in attachment plots."
    for repo_dict in repo_dict_data:
        repo_notify = repo_dict["notify"]
        for notify_email in repo_notify["TO"]:
            if notify_email not in author_notifications:
                author_notifications[notify_email] = {"body": "", "CC": [], "Reply-to": [], "attachments": []}
            # email_body = format_statistics(repo_dict["stats"])
            # updated_body = author_notifications[notify_email]["body"] + email_body
            updated_body = email_body
            updated_CC = list(set(author_notifications[notify_email]["CC"] + repo_notify["CC"]))
            updated_ReplyTo = list(set(author_notifications[notify_email]["Reply-to"] + repo_notify["Reply-to"]))
            updated_attachments = list(set(author_notifications[notify_email]["attachments"]
                                           + repo_dict["activity_plot"]))
            author_notifications[notify_email] = {"body": f"{updated_body}", "CC": updated_CC,
                                                  "Reply-to": updated_ReplyTo, "attachments": updated_attachments}
            print(f"Repo {repo_dict['name']}: Preparing email to {notify_email}"
                  + f" and CC: {author_notifications[notify_email]['CC']}")

    for notify_email in author_notifications.keys():
        # Send the statistics via email
        email_body = author_notifications[notify_email]["body"]
        # Remove duplicates using set
        CC_list = author_notifications[notify_email]["CC"]
        reply_to_list = author_notifications[notify_email]["Reply-to"]
        attachments = author_notifications[notify_email]["attachments"]
        if args.notify:
            print(f"Sending email to {notify_email} and CC: {CC_list} with Reply-to: {reply_to_list}")
            email_routing_dict = {"TO": [notify_email], "CC": CC_list, "Reply-to": reply_to_list}
            now_datestr = now.strftime("%Y-%m-%d")
            email_subject = f"Daily Code and Writing Productivity Report for {now_datestr}"
            send_email(email_subject, email_body, email_routing_dict, email_auth_dict, attachments)
        else:
            print(f"** REPORT FOR AUTHOR {notify_email} **:\n {email_body}")

    # Remove temporary image files created for email attachments
    for repo_dict in repo_dict_data:
        if "activity_plot" in repo_dict:
            try:
                os.remove(repo_dict["activity_plot"])
                print(f"Temporary image for email attachments {repo_dict['activity_plot']} deleted successfully.")
            except FileNotFoundError:
                print("File not found.")
            except PermissionError:
                print("You don't have permission to delete this file.")
            except Exception as e:
                print("An error occurred:", e)
