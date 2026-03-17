import os
import smtplib
from datetime import datetime
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


# df is a 1 row data frame
def single_crash_email(df, council_district, recipient_email):
    row = df.iloc[0]
    location = get_crash_location(row)
    time_crash = str(row["crash_time"])
    today = datetime.now().strftime("%Y-%m-%d")

    msg = MIMEText(
        f"""Dear Council Member,

    On {today} at {time_crash}, there was a motor vehicle crash at {location} in your district that resulted in an injury.
    Since 2014, New York has adopted a Vision Zero policy affirming that motor vehicle crashes are preventable. Could this crash have been prevented?

    Thank you for your time and attention,
    The Crash Crew

    """
    )

    msg["Subject"] = f"Vision Zero: Injury Crash in District {council_district} {today}"
    msg["From"] = os.getenv("GMAIL_EMAIL")
    msg["To"] = recipient_email

    return msg


def multiple_crash_email(df, council_district, recipient_email):
    today = datetime.now().strftime("%Y-%m-%d")
    num_crashes = len(df)

    crash_details = []
    for _, row in df.iterrows():
        location = get_crash_location(row)
        time_crash = str(row["crash_time"])
        injured = int(row.get("number_of_persons_injured", 0))
        killed = int(row.get("number_of_persons_killed", 0))
        crash_details.append(
            f"    - {time_crash} at {location}: {injured} injured, {killed} killed"
        )

    crash_list = "\n".join(crash_details)

    msg = MIMEText(
        f"""Dear Council Member,

    On {today}, there were {num_crashes} motor vehicle crashes in your district that resulted in injuries:

{crash_list}

    Since 2014, New York has adopted a Vision Zero policy affirming that motor vehicle crashes are preventable. Could these crashes have been prevented?

    Thank you for your time and attention,
    The Crash Crew

    """
    )

    msg["Subject"] = (
        f"Vision Zero: {num_crashes} Injury Crashes in District {council_district} {today}"
    )
    msg["From"] = os.getenv("GMAIL_EMAIL")
    msg["To"] = recipient_email

    return msg


# sends an email about injury accidents to the council member of that district
def send_injury_email(df, council_district):
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")

    # get injury crashes from today in the given council district
    df_district = df[df["CounDist"] == council_district]

    # get the council member's email from the data
    district_emails = df_district["email"].dropna().unique()
    if len(district_emails) == 0:
        print(f"No email found for district {council_district}, skipping.")
        return
    recipient_email = district_emails[0]

    # crash_date may be in ISO format (e.g. "2026-03-10T00:00:00.000"), so
    # compare only the date portion
    df_injury_cd_current = df_district[
        (df_district["crash_date"].str[:10] == today)
        & (
            (df_district["number_of_persons_injured"].astype(int)
             + df_district["number_of_persons_killed"].astype(int))
            > 0
        )
    ]

    # if there were no injury accidents in the council district on this day, then return
    if df_injury_cd_current.shape[0] == 0:
        return
    # if there was exactly 1 injury accident, send that kind of email
    elif df_injury_cd_current.shape[0] == 1:
        msg = single_crash_email(df_injury_cd_current, council_district, recipient_email)
    else:
        msg = multiple_crash_email(df_injury_cd_current, council_district, recipient_email)

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = os.getenv("GMAIL_EMAIL")
    SENDER_PASSWORD = os.getenv("APP_PASSWORD")

    # Send email
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())

    print(f"Email sent to {recipient_email} for district {council_district}!")
