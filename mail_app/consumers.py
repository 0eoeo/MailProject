import imaplib
import email
import html2text
from email.header import decode_header
from email import utils
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import datetime as dt
import json
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mail_project.settings")
django.setup()

from .models import MailMessages


def parse_email(msg):
    email_id = msg["Message-Id"]
    email_date = utils.parsedate_to_datetime(msg["date"]).date()

    try:
        email_subject = decode_header(msg["subject"])[0][0].decode()
    except:
        email_subject = msg["subject"]

    files = []
    message_text = ""

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition"))

        if content_type == "text/plain" and "attachment" not in content_disposition:
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset()
            message_text += (
                payload.decode(charset) if charset else payload.decode("utf-8")
            )

        elif content_type == "text/html" and "attachment" not in content_disposition:
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset()
            html_content = (
                payload.decode(charset) if charset else payload.decode("utf-8")
            )

            html_to_text_converter = html2text.HTML2Text()
            html_to_text_converter.ignore_links = True
            html_to_text_converter.ignore_images = True
            message_text += html_to_text_converter.handle(html_content)

        if part.get_content_maintype() != "multipart" and part.get(
            "Content-Disposition"
        ):
            try:
                files.append(decode_header(part.get_filename())[0][0].decode())
            except:
                files.append(part.get_filename())

    return email_id, email_subject, email_date, message_text, files


class MailConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        address = data.get("address")
        password = data.get("password")
        user_id = data.get("user_id")

        if action == "fetch_messages" and address and password and user_id:
            await self.fetch_messages(address, password, user_id)

    async def fetch_messages(self, address, password, user_id):
        mailbox = address.split("@")[1]
        mail = imaplib.IMAP4_SSL(f"imap.{mailbox}")
        mail.login(address, password)
        mail.select("inbox")

        result, data = mail.search(None, "ALL")
        if result != "OK":
            await self.send_error("Failed to retrieve emails.")
            return

        mail_ids = data[0].split()
        total_messages = len(mail_ids)
        checked_count = 0
        messages = []

        for email_id in mail_ids:
            result, data = mail.fetch(email_id, "(RFC822)")
            if result != "OK":
                await self.send_error("Failed to fetch the email.")
                continue

            msg = email.message_from_bytes(data[0][1])
            messages.append(msg)
            checked_count += 1
            await self.update_progress(checked_count)

        await self.process_messages(messages, total_messages, user_id)

    async def process_messages(self, messages, total_messages, user_id):
        checked_count = total_messages

        for msg in messages:
            email_id, email_subject, email_date, message_text, files = parse_email(msg)

            message = await self.create_mail_message(
                message_id=email_id,
                subject=email_subject,
                send_date=email_date,
                recieve_date=dt.datetime.today().date(),
                message=message_text,
                files=files,
                user_id=user_id,
            )

            if message:
                checked_count -= 1
                await self.send_message(message, total_messages, checked_count)

        await self.finalize_progress(total_messages, checked_count)

    async def send_message(self, message, total_messages, checked_count):
        await self.send(
            text_data=json.dumps(
                {
                    "message": {
                        "id": message.id,
                        "subject": message.subject,
                        "send_date": str(message.send_date),
                        "recieve_date": str(message.recieve_date),
                        "message": message.message[:300] + "..."
                        if len(message.message) > 300
                        else message.message,
                        "files": message.files if message.files else ["-"],
                    },
                    "progress": (total_messages - checked_count) / total_messages * 100,
                    "checked_count": checked_count,
                }
            )
        )

    async def update_progress(self, checked_count):
        await self.send(text_data=json.dumps({"checked_count": checked_count}))

    async def finalize_progress(self, total_messages, checked_count):
        total_saved = total_messages - checked_count
        await self.send(
            text_data=json.dumps(
                {
                    "total_count": total_messages,
                    "total_saved": total_saved,
                    "progress": 100 if total_saved > 0 else 0,
                    "checked_count": 0,
                }
            )
        )

    async def send_error(self, message):
        await self.send(text_data=json.dumps({"error": message}))

    @database_sync_to_async
    def create_mail_message(
        self, message_id, subject, send_date, recieve_date, message, files, user_id
    ):
        if not MailMessages.objects.filter(message_id=message_id).exists():
            return MailMessages.objects.create(
                message_id=message_id,
                subject=subject,
                send_date=send_date,
                recieve_date=recieve_date,
                message=message,
                files=files,
                user_id=user_id,
            )
