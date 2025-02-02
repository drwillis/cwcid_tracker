# import os
from collections import defaultdict
import time
import re
import datetime
import matplotlib.pyplot as plt
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import urllib.request
import smtplib
from email.message import EmailMessage

# Set up Google Docs API authentication
SCOPES = ['https://www.googleapis.com/auth/documents.readonly',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/drive.metadata.readonly']

DOCUMENT_ID = '1h4dQH9U9wgkN7xnqThw4GAsKyoEeGUHm9BcGEFgRkaA'  # Replace with your Google Doc ID

#  Increase this if you are getting HTTP 429 errors: "429 Too Many Requests"
WAIT_TIME = 5

from cwcid_default_auth_credentials import google_auth_servicekey_dict

# Authenticate
credentials_info = google_auth_servicekey_dict
credentials = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
# credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
print("🔑 Authenticating with OAuth 2.0...")
docs_service = build('docs', 'v1', credentials=credentials)
drive_service_v2 = build('drive', 'v2', credentials=credentials)
drive_service_v3 = build('drive', 'v3', credentials=credentials)


# Fetch document revisions (edits history)
def get_revision_history_v3(doc_id):
    try:
        response = drive_service_v3.revisions().list(fileId=doc_id).execute()
        revisions = response.get('revisions', [])

        change_log = []
        for revision in revisions:
            timestamp = revision.get('modifiedTime', 'Unknown Time')
            author = revision.get('lastModifyingUser', {}).get('displayName', 'Unknown')
            email = revision.get('lastModifyingUser', {}).get('emailAddress', 'Unknown Email')
            size = revision.get('size', 'Unknown Size')
            revision_id = revision.get('id')

            change_log.append({
                'Revision ID': revision_id,
                'Timestamp': timestamp,
                'Author': author,
                'Email': email,
                'Size (bytes)': size
            })

        return change_log

    except Exception as e:
        print(f"❌ Error fetching revision history: {e}")
        return []


def get_revision_history_v2(doc_id):
    try:
        response = drive_service_v2.revisions().list(fileId=doc_id).execute()
        revisions = response.get('items', [])  # API v2 uses 'items' instead of 'revisions'

        change_log = []
        for rev in revisions:
            timestamp = rev.get('modifiedDate', 'Unknown Time')
            author_info = rev.get('lastModifyingUser', {})
            author = author_info.get('displayName', 'Unknown')
            email = author_info.get('emailAddress', 'Unknown Email')
            size = rev.get('fileSize', 'Unknown Size')
            revision_id = rev.get('id')

            change_log.append({
                'Revision ID': revision_id,
                'Timestamp': timestamp,
                'Author': author,
                'Email': email,
                'Size (bytes)': size
            })

        return change_log

    except Exception as e:
        print(f"❌ Error fetching revision history: {e}")
        return []


# Categorize changes by time periods
def categorize_changes(changes):
    today = datetime.datetime.now().date()
    stats = {}

    for change in changes:
        timestamp = datetime.datetime.strptime(change['Timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
        author = change['Author']

        if author not in stats:
            stats[author] = {'daily': 0, 'weekly': 0, 'monthly': 0, 'yearly': 0}

        if timestamp == today:
            stats[author]['daily'] += 1
        if (today - timestamp).days <= 7:
            stats[author]['weekly'] += 1
        if timestamp.month == today.month and timestamp.year == today.year:
            stats[author]['monthly'] += 1
        if timestamp.year == today.year:
            stats[author]['yearly'] += 1

    return stats


# 🔹 Fetch document content at a specific revision
def get_revision_text(doc_id, revision_id):
    try:
        # Google Docs text can be exported in plaintext
        revision_content = drive_service_v2.revisions().get(fileId=doc_id, revisionId=revision_id).execute()
        # revision_content = drive_service_v3.revisions().get_media(fileId=doc_id, revisionId=revision_id)
        # download_url = f"https://www.googleapis.com/drive/v3/files/{doc_id}/revisions/{revision_id}?alt=media"
        # download_url = f"https://www.googleapis.com/drive/v2/files/{doc_id}/revisions/{revision_id}"
        download_url = f"https://docs.google.com/feeds/download/documents/export/Export?id={doc_id}&revision={revision_id}&exportFormat=txt"

        if not download_url:
            print(f"⚠️ Revision {revision_id} has no downloadable content.")
            return ""
        try:
            # Fetch the content from the URL
            import requests
            headers = {
                "Authorization": f"Bearer {credentials.token}",
                # "Content-Type": "application/x-www-form-urlencoded",
                "Content-Type": "text/plain",
                # "Accept": "Accept=text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            # req = urllib.request.Request(download_url, headers=headers)
            # with urllib.request.urlopen(req) as response:
            #     data = response.read()
            # Process the data
            # print(data)
            response = requests.get(download_url, headers=headers)
        except Exception as e:
            print(f"❌ Error downloading revision {revision_id}: {e}")
            return None
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"⚠️ Failed to fetch content for revision {revision_id}. HTTP {response.status_code}")
            return ""

    except Exception as e:
        print(f"❌ Error fetching revision {revision_id}: {e}")
        return ""


# 🔹 Compute word count from text
def count_words(text):
    return len(re.findall(r'\b\w+\b', text))


# 🔹 Track word contributions per author
def compute_word_contributions(doc_id, revisions):
    contributions = defaultdict(lambda: defaultdict(int))  # {author: {date: words_added}}
    # prev_text = get_revision_text(doc_id, revisions[0]['Revision ID'])
    if not revisions:
        return contributions
    prev_text = ""  # Stores the previous revision text
    for rev in revisions:  # Process from second revision onward
        id = rev['Revision ID']
        modified_time = rev['Timestamp']
        author = rev['Email']
        date = datetime.datetime.strptime(modified_time, "%Y-%m-%dT%H:%M:%S.%fZ").date()

        time.sleep(WAIT_TIME)
        current_text = get_revision_text(doc_id, rev['Revision ID'])
        if not current_text:
            continue

        # Compute word difference
        prev_word_count = count_words(prev_text)
        current_word_count = count_words(current_text)

        words_added = current_word_count - prev_word_count

        contributions[author][date] += words_added
        # if author not in word_contributions:
        #     word_contributions[author] = 0
        # word_contributions[author] += max(0, words_added)  # Ignore deletions for now

        # Update previous state
        prev_text = current_text
        # prev_word_count = current_word_count

    return contributions


# 🔹 Generate Time-Series Bar Chart
def generate_chart(contributions):
    dates = sorted({date for author in contributions for date in contributions[author]})
    authors = list(contributions.keys())

    # Create dataset for each author
    data = {author: [contributions[author].get(date, 0) for date in dates] for author in authors}

    # Plot
    plt.figure(figsize=(12, 6))
    bottom = [0] * len(dates)

    for author in authors:
        plt.bar(dates, data[author], bottom=bottom, label=author)
        bottom = [bottom[i] + data[author][i] for i in range(len(dates))]

    plt.xlabel("Date")
    plt.ylabel("Words Added")
    plt.title("Word Contributions Over Time")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    chart_path = "word_contributions.png"
    plt.savefig(chart_path)
    print(f"📊 Chart saved: {chart_path}")

    return chart_path


def send_email_with_chart(image_path):
    # 🔹 Email Configuration
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "your_email@gmail.com"
    SENDER_PASSWORD = "your_app_password"
    RECIPIENT_EMAIL = "recipient_email@gmail.com"
    try:
        msg = EmailMessage()
        msg["Subject"] = "Google Doc Word Contribution Report"
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        msg.set_content("Attached is the Google Doc word contribution report with daily statistics.")

        # Attach the image
        with open(image_path, "rb") as img:
            msg.add_attachment(img.read(), maintype="image", subtype="png", filename="word_contributions.png")

        # Send Email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"📧 Email sent successfully to {RECIPIENT_EMAIL}")

    except Exception as e:
        print(f"❌ Error sending email: {e}")


# Generate and save report
def generate_report(changes, stats):
    df_changes = pd.DataFrame(changes)
    df_stats = pd.DataFrame.from_dict(stats, orient='index')
    df_stats.index.name = 'Author'
    df_stats.reset_index(inplace=True)

    # df_changes.to_csv('detailed_change_log.csv', index=False)
    # df_stats.to_csv('summary_report.csv', index=False)

    print(f"📊 Detailed Change Log saved as `detailed_change_log.csv`")
    print(df_changes)
    print(f"📊 Summary Report saved as `summary_report.csv`")
    print(df_stats)


# Execute tracking and report generation
if __name__ == '__main__':
    print("📡 Fetching detailed revision history...")
    changes = get_revision_history_v2(DOCUMENT_ID)

    if not changes:
        print("❌ No changes found.")
    else:
        print(f"✅ Processing {len(changes)} changes...")
        print(f"✅ Processing {len(changes)} revisions...")
        word_contributions = compute_word_contributions(DOCUMENT_ID, changes)

        if word_contributions:
            print("📊 Generating word contribution chart...")
            chart_path = generate_chart(word_contributions)

            # print("📧 Sending email with attachment...")
            # send_email_with_chart(chart_path)
        # generate_report(changes, word_contributions)
        # stats = categorize_changes(changes)
        # generate_report(changes, stats)
