import os
import base64
import smtplib

protocol = "ssl"
svr = "smtp.mediacenter.hu"
uid = "karat"
pwd = "3!"

if protocol = "ssl":
    mailer = smtplib.SMTP_SSL(svr)
elif protocol = "starttls":
    mailer = smtplib.SMTP(svr)
    mailer.starttls()
elif protocol = "plain":
    mailer = smtplib.SMTP(svr)
mailer.login(uid, pwd)

sender = "pwdreset@technocar.hu"
login = "jason"
token = "aabb1122"
recip = "jason@technocar.hu"
mime_sep = base64.urlsafe_b64encode(os.urandom(15))

# TODO what if we don't include From
email = f"""From: {sender}
Content-Type: multipart/alternative; boundary="{mime_sep}"
Subject: I4C jelszó

This is a multi-part message in MIME format.

{mime_sep}
Content-Type: text/plain; charset=UTF-8

link: https://i4c.technocar.hu/pwdreset?token={token}&loginname={login}

{mime_sep}
Content-Type: text/html; charset=UTF-8

<html>
<a href="https://i4c.technocar.hu/pwdreset?token={token}&loginname={login}">
https://i4c.technocar.hu/pwdreset?token={token}&loginname={login}
</a>
</html>
{mime_sep}--
"""
mailer.sendmail(sender, [recip], email)
