import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv


def get_crash_location(row):
    """Get a human-readable location string from a crash row."""
    location = str(row.get("cross_street_name", ""))
    if location == "" or location == "nan":
        on_street = str(row.get("on_street_name", ""))
        off_street = str(row.get("off_street_name", ""))
        location = f"{on_street} & {off_street}"
    return location


def single_crash_email(df, council_district, recipient_email):
    row = df.iloc[0]
    location = get_crash_location(row)
    time_crash = str(row["crash_time"])
    crash_date = str(row["crash_date"])[:10]

    msg = MIMEText(
        f"""Dear Council Member,

    On {crash_date} at {time_crash}, there was a motor vehicle crash at {location} in your district that resulted in an injury.
    Since 2014, New York has adopted a Vision Zero policy affirming that motor vehicle crashes are preventable. Could this crash have been prevented?

    Thank you for your time and attention,
    The Crash Crew

    """
    )

    msg["Subject"] = f"Vision Zero: Injury Crash in District {council_district} {crash_date}"
    msg["From"] = os.getenv("GMAIL_EMAIL")
    msg["To"] = recipient_email

    return msg


def multiple_crash_email(df, council_district, recipient_email):
    num_crashes = len(df)

    crash_details = []
    for _, row in df.iterrows():
        location = get_crash_location(row)
        time_crash = str(row["crash_time"])
        crash_date = str(row["crash_date"])[:10]
        injured = int(row.get("number_of_persons_injured", 0))
        killed = int(row.get("number_of_persons_killed", 0))
        crash_details.append(
            f"    - {crash_date} {time_crash} at {location}: {injured} injured, {killed} killed"
        )

    crash_list = "\n".join(crash_details)

    msg = MIMEText(
        f"""Dear Council Member,

    There were {num_crashes} new motor vehicle crashes in your district that resulted in injuries:

{crash_list}

    Since 2014, New York has adopted a Vision Zero policy affirming that motor vehicle crashes are preventable. Could these crashes have been prevented?

    Thank you for your time and attention,
    The Crash Crew

    """
    )

    msg["Subject"] = (
        f"Vision Zero: {num_crashes} New Injury Crashes in District {council_district}"
    )
    msg["From"] = os.getenv("GMAIL_EMAIL")
    msg["To"] = recipient_email

    return msg


def send_injury_email(df):
    """Send an email about new injury crashes to the council member of that district.

    df should be pre-filtered to only contain new injury crashes for a single district.
    """
    load_dotenv()

    district_emails = df["email"].dropna().unique()
    if len(district_emails) == 0:
        return
    recipient_email = district_emails[0]

    council_district = int(df["CounDist"].iloc[0])

    if len(df) == 1:
        msg = single_crash_email(df, council_district, recipient_email)
    else:
        msg = multiple_crash_email(df, council_district, recipient_email)

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = os.getenv("GMAIL_EMAIL")
    SENDER_PASSWORD = os.getenv("APP_PASSWORD")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())

    print(f"Email sent to {recipient_email} for district {council_district}!")
