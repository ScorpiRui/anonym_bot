from django.db import models

class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    referral_link = models.CharField(max_length=100, unique=True)

class ActiveChat(models.Model):
    referrer = models.ForeignKey(User, related_name='referrer', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='user', on_delete=models.CASCADE)
