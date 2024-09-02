from django.db import models
from django.contrib.postgres.fields import ArrayField


class MailAddresses(models.Model):
    id = models.AutoField(primary_key=True)
    address = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = '"public"."mail_addresses"'


class MailMessages(models.Model):
    id = models.AutoField(primary_key=True)
    message_id = models.CharField(unique=True)
    subject = models.CharField()
    send_date = models.DateField()
    recieve_date = models.DateField()
    message = models.CharField()
    files = ArrayField(models.CharField())
    user = models.ForeignKey(MailAddresses, models.DO_NOTHING,
                             to_field='id')

    class Meta:
        managed = False
        db_table = '"public"."mail_messages"'
