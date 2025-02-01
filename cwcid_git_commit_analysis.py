import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
from datetime import datetime, timedelta
import git
import os


def clone_or_pull_repo(repo_url, repo_auth, local_path, username, token):
    """
    Clone the repository if not already cloned, or pull the latest changes.
    """
    try:
        # Prepare the authenticated URL
        if "https://" in repo_url and repo_auth == "Overleaf":
            authenticated_url = repo_url.replace(
                "https://", f"https://{username}:{token}@"
            )
        elif "https://" in repo_url and repo_auth == "GithubPublic":
            authenticated_url = repo_url
        else:
            raise ValueError("Invalid HTTPS URL provided for the repository.")

        # Clone the repository if not already cloned
        if not os.path.exists(local_path):
            print(f"Cloning repository from {repo_url} to {local_path}...")
            git.Repo.clone_from(authenticated_url, local_path)
        else:
            print(f"Repository already cloned at {local_path}. Pulling latest changes...")
            repo = git.Repo(local_path)
            repo.remotes.origin.set_url(authenticated_url)  # Update remote URL
            repo.remotes.origin.pull()

        return git.Repo(local_path)

    except Exception as e:
        print(f"Error: {e}")
        return None


def compute_statistics(repo, start_date, end_date):
    """
    Compute statistics aggregated by username.
    """
    statistics = defaultdict(lambda: {"line_changes": 0, "commits": []})

    # Iterate through all commits
    for commit in repo.iter_commits():
        commit_date = datetime.fromtimestamp(commit.committed_date)
        if start_date <= commit_date <= end_date:
            author = commit.author.name if commit.author else "Unknown"
            stats = commit.stats.total

            # Update statistics
            statistics[author]["line_changes"] += stats["insertions"] + stats["deletions"]
            statistics[author]["commits"].append({
                "date": commit_date.strftime("%Y-%m-%d %H:%M:%S"),
                "message": commit.message.strip(),
                "insertions": stats["insertions"],
                "deletions": stats["deletions"],
            })

    return statistics


def send_email(subject, body, notify, email_auth_dict):
    """
    Send an email with the given subject and body to the specified recipients.
    """
    smtp_server = email_auth_dict["smtp_server"]
    smtp_port = email_auth_dict["smtp_port"]
    sender_email = email_auth_dict["sender_email"]
    sender_password = email_auth_dict["sender_password"]

    # Prepare email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(notify["TO"])
    msg["CC"] = ", ".join(notify.get("CC", []))
    if "Reply-to" in notify:
        msg["Reply-to"] = ", ".join(notify["Reply-to"])
    msg["Subject"] = subject

    # Add the email body
    # print(f"email body: {body}")
    msg.attach(MIMEText(body, "plain"))

    # Send email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # server.set_debuglevel(10)
            if smtp_port == 587:
                server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, notify["TO"] + notify.get("CC", []), msg.as_string())
            print(f"Email sent successfully to: {', '.join(notify['TO'])}")

    except Exception as e:
        print(f"Error sending email: {e}")


def format_statistics(statistics):
    """
    Format the aggregated statistics as a string for the email body.
    """
    # email_body = f"{header}:\n"
    email_body = ""
    for author, data in statistics.items():
        email_body += f"Author: {author}\n"
        email_body += f"  Total Line Changes: {data['line_changes']}\n"
        email_body += f"  Commits:\n"
        for commit in data["commits"]:
            email_body += f"    - Commit Date: {commit['date']}, Message: {commit['message']}\n"
            email_body += f"      Insertions: {commit['insertions']}, Deletions: {commit['deletions']}\n"
        email_body += "\n"
    return email_body


def display_statistics(statistics, group_by):
    """
    Display statistics grouped by time period.
    """
    print(f"\nStatistics grouped by {group_by.capitalize()}:\n")
    for time_group, authors in statistics.items():
        print(f"{group_by.capitalize()} Group: {time_group}")
        for author, data in authors.items():
            print(f"  Author: {author}")
            print(f"    Total Line Changes: {data['line_changes']}")
            print(f"    Commits:")
            for commit in data["commits"]:
                print(f"      - Date: {commit['date']}, Message: {commit['message']}")
                print(f"        Insertions: {commit['insertions']}, Deletions: {commit['deletions']}")
        print()


def main(repo_dict_data, email_auth_dict, overleaf_auth_dict, email_notifications):
    # repo_url = "https://git.overleaf.com/your-repository-id"  # Replace with your Overleaf Git repository URL
    username = overleaf_auth_dict["username"]  # Replace with your Overleaf username or email
    token = overleaf_auth_dict["token"]  # Replace with your personal access token

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

    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    author_notifications = {}
    # Clone or pull the repository
    for repo_dict in repo_dict_data:
        repo_type = repo_dict["type"]
        repo_auth = repo_dict["auth"]
        repo_name = repo_dict["name"]
        repo_url = repo_dict["url"]
        repo_notify = repo_dict["notify"]
        local_path = "./git_repos/" + repo_name  # Specify a directory to clone the repository
        repo = clone_or_pull_repo(repo_url, repo_auth, local_path, username, token)
        if not repo:
            return

        # Compute statistics for the past week
        repo_stats = f"Repository \"{repo_name}\":\n"
        for time_dict in time_interval_dicts:
            start_time = time_dict["Time Start"]
            period_str = time_dict["Period"]
            statistics = compute_statistics(repo, start_time, now)
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            repo_stats += f"{period_str} Statistics from {start_time_str} to {now_str}:\n\n"
            # Format the statistics
            repo_stats += format_statistics(statistics)

        for notify_email in repo_notify["TO"]:
            if notify_email not in author_notifications:
                author_notifications[notify_email] = {}
                author_notifications[notify_email]["body"] = ""
                author_notifications[notify_email]["CC"] = []
                # author_notifications[notify_email]["Reply-to"] = None
            author_notifications[notify_email]["body"] += repo_stats
            if "CC" in repo_notify:
                author_notifications[notify_email]["CC"] += repo_notify["CC"]
            if "Reply-to" in repo_notify:
                author_notifications[notify_email]["Reply-to"] = repo_notify["Reply-to"]
            # print(f"Preparing email to {notify_email} and CC: {author_notifications[notify_email]['CC']}")

    if email_notifications == True:
        for notify_email in author_notifications.keys():
            # Send the statistics via email
            email_body = author_notifications[notify_email]["body"]
            # Remove duplicates using set
            if "CC" in author_notifications[notify_email]:
                CC_list = list(set(author_notifications[notify_email]["CC"]))
            else:
                CC_list = []
            if "Reply-to" in author_notifications[notify_email]:
                reply_to = author_notifications[notify_email]["Reply-to"]
            else:
                reply_to = None
            print(f"Sending email to {notify_email} and CC: {CC_list} with Reply-to: {reply_to}")
            email_routing_dict = {"TO": [notify_email], "CC": CC_list, "Reply-to": reply_to}
            now_datestr = now.strftime("%Y-%m-%d")
            email_subject = f"Daily Code and Writing Productivity Report for {now_datestr}"
            send_email(email_subject, email_body, email_routing_dict, email_auth_dict)


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
    main(repo_dict_data, email_auth_dict, overleaf_auth_dict, args.notify)
