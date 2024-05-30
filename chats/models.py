# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError

# models
from users.models import CustomUser


class Chat(models.Model):
    
    participants = models.ManyToManyField(CustomUser, related_name='direct_messages')

    # class account id 
    chat_id = models.CharField(max_length=15, unique=True)

    class Meta:
        verbose_name = _('chat')
        verbose_name_plural = _('chats')

    def __str__(self):
        return self.name

    # class account id creation handler
    def save(self, *args, **kwargs):
        if not self.chat_id:
            self.chat_id = self.generate_unique_account_id('CH')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                self.chat_id = self.generate_unique_account_id('CH') # Chat
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create class with unique account ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Chat.objects.filter(chat_id=account_id).exists():
                return account_id
            

class Message(models.Model):
    
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat_messages')

    sent_by = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)

    Message = models.TextField(max_length=1024)
    read = models.BooleanField(default=False)

    sent_at = models.DateField(auto_now_add=True)
