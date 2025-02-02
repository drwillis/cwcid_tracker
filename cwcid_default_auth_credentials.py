# Example:
#   smtp_server = "smtp.gmail.com"
#   smtp_port = 587
#   sender_email = "me@gmail.com"  # Replace with your email
#   sender_password = "aaaa bbbb cccc dddd"  # Replace with your email password or app-specific password
email_auth_dict = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "me@gmail.com",  # Replace with your email
    "sender_password": "aaaa bbbb cccc dddd"  # Replace with your email password or app-specific password
}
# Replace with your Git repository username and access token
overleaf_auth_dict = {
    "username": "git",
    "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
# google JSON authorization credentials allow access to Google drive
google_auth_servicekey_dict = {
  "type": "service_account",
  "project_id": "my_project_id",
  "private_key_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n<<KEYDATAGOESHERE>>\n-----END PRIVATE KEY-----\n",
  "client_email": "xxxxxxxxxxxxxxxxxxxxxxxx.iam.gserviceaccount.com",
  "client_id": "xxxxxxxxxxxxxxxxxxx",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "universe_domain": "googleapis.com"
}
