from django.contrib import admin
from chat.models import Conversation, Message

admin.site.register(Conversation)
admin.site.register(Message)
