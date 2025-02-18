import argparse
from collections import defaultdict
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import git
import matplotlib
matplotlib.use('TkAgg', force=True)
# matplotlib.use('Agg', force=True)
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os
from pathlib import Path
import random
import smtplib
import string


def generate_random_filename(length=10):
    """Generates a random filename of specified length."""
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))


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


def gather_statistics(repo):  # , start_date, end_date):
    """
    Compute statistics aggregated by username.
    """
    statistics = {}
    # Iterate through all commits
    for commit in repo.iter_commits():
        commit_date = datetime.fromtimestamp(commit.committed_date)
        author = commit.author.name if commit.author else "Unknown"
        stats = commit.stats.total
        # Update statistics
        if author not in statistics:
            statistics[author] = {"line_changes": 0, "commits": []}
        statistics[author]["line_changes"] += stats["insertions"] + stats["deletions"]
        statistics[author]["commits"].append({
            "date": commit_date.strftime("%Y-%m-%d %H:%M:%S"),
            "message": commit.message.strip(),
            "insertions": stats["insertions"],
            "deletions": stats["deletions"],
        })

    return statistics


def send_email(subject, body, notify, email_auth_dict, attachments):
    """
    Send an email with the given subject and body to the specified recipients.
    """
    smtp_server = email_auth_dict["smtp_server"]
    smtp_port = email_auth_dict["smtp_port"]
    sender_email = email_auth_dict["sender_email"]
    sender_password = email_auth_dict["sender_password"]
    # notify["TO"] = ["arwillis@charlotte.edu"]
    # Prepare email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(notify["TO"])
    msg["CC"] = ", ".join(notify.get("CC", []))
    if "Reply-to" in notify:
        msg["Reply-to"] = ", ".join(notify["Reply-to"])
    msg["Subject"] = subject

    msg.attach(MIMEText(body))

    for path in attachments:
        part = MIMEBase('application', "octet-stream")
        with open(path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename={}'.format(Path(path).name))
        msg.attach(part)

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


def plot_change_history(repo_data, image_folder="./images"):
    stats = repo_data["stats"]
    # Aggregate contributions per day per author (separate insertions & deletions)
    daily_insertions = defaultdict(lambda: defaultdict(int))
    daily_deletions = defaultdict(lambda: defaultdict(int))

    for author, data in stats.items():
        for commit in data['commits']:
            commit_date = datetime.strptime(commit['date'], '%Y-%m-%d %H:%M:%S').date()
            daily_insertions[commit_date][author] += commit['insertions']
            daily_deletions[commit_date][author] -= commit['deletions']
    # Sort dates in ascending order
    sorted_dates = sorted(set(daily_insertions.keys()).union(set(daily_deletions.keys())))

    # Get unique authors
    authors = sorted(set(author for contributions in daily_insertions.values() for author in contributions))

    # Assign colors dynamically
    color_palette = list(mcolors.TABLEAU_COLORS.values())  # Use Tableau colors for better contrast
    colors = {author: color_palette[i % len(color_palette)] for i, author in enumerate(authors)}

    # Prepare data for stacked bars
    insertions_data = {author: [] for author in authors}
    deletions_data = {author: [] for author in authors}

    for date in sorted_dates:
        for author in authors:
            insertions_data[author].append(daily_insertions[date].get(author, 0))
            deletions_data[author].append(daily_deletions[date].get(author, 0))

    # Plot stacked bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    bottom_insertions = [0] * len(sorted_dates)
    bottom_deletions = [0] * len(sorted_dates)
    print(sorted_dates)
    for author in authors:
        # Plot insertions
        ax.bar(sorted_dates, insertions_data[author], bottom=bottom_insertions, label=f'{author} (Insertions)',
               color=colors[author])
        bottom_insertions = [bottom_insertions[i] + insertions_data[author][i] for i in range(len(sorted_dates))]

        # Plot deletions (use a darker shade of the same color)
        ax.bar(sorted_dates, deletions_data[author], bottom=bottom_deletions, label=f'{author} (Deletions)',
               color=mcolors.to_rgba(colors[author], 0.6))
        bottom_deletions = [bottom_deletions[i] + deletions_data[author][i] for i in range(len(sorted_dates))]

    # Formatting the plot
    plt.xlabel('Date')
    plt.ylabel('Total Contributions')
    plt.title(f'Repository {repo_data["name"]}\nDaily Insertions and Deletions per Author')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Optimized legend placement (outside plot)
    plt.legend(title="Contributions", bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)

    # Adjust layout to fit legend
    plt.tight_layout()
    # Save the plot as a PNG file
    random_filename = generate_random_filename(15)
    if not os.path.isdir(image_folder):
        os.makedirs(image_folder)
    output_file = os.path.join(image_folder, f'repo_stats_{random_filename}.png')
    plt.savefig(output_file)
    repo_data["activity_plot"] = [output_file]
    print(repo_data["activity_plot"])
    # plt.show()


def track_git_changes(repo_dict_data, overleaf_auth_dict, folder="./git_repos/"):
    # repo_url = "https://git.overleaf.com/your-repository-id"  # Replace with your Overleaf Git repository URL
    username = overleaf_auth_dict["username"]  # Replace with your Overleaf username or email
    token = overleaf_auth_dict["token"]  # Replace with your personal access token

    statistics = {}
    # Clone or pull the repository
    for repo_dict in repo_dict_data:
        # repo_type = repo_dict["type"]
        # repo_notify = repo_dict["notify"]
        repo_auth = repo_dict["auth"]
        repo_name = repo_dict["name"]
        repo_url = repo_dict["url"]
        local_path = folder + repo_name  # Specify a directory to clone the repository
        repo = clone_or_pull_repo(repo_url, repo_auth, local_path, username, token)
        if not repo:
            return
        # Compute statistics for the past week
        repo_dict["stats"] = gather_statistics(repo)
    return statistics


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

    # day_start = now - timedelta(days=1)
    # week_start = now - timedelta(days=7)
    # month_start = now - timedelta(days=30)
    # year_start = now - timedelta(days=365)
    # time_interval_dicts = [
    #     {
    #         "Time Start": day_start,
    #         "Period": "Daily"
    #     }, {
    #         "Time Start": week_start,
    #         "Period": "Weekly"
    #     }, {
    #         "Time Start": month_start,
    #         "Period": "Monthly"
    #     }, {
    #         "Time Start": year_start,
    #         "Period": "Yearly"
    #     }
    # ]

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
