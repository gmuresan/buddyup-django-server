from django.contrib import admin
from chat.models import Conversation, Message


class ConversationAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)

admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Message)
