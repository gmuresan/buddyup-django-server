from django.contrib import admin
from chat.models import Conversation, Message


class ConversationAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'members')

admin.site.register(Conversation, ConversationAdmin)

class MessageAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'conversation', )

admin.site.register(Message, MessageAdmin)
