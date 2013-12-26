from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from api import *

from buddyup import settings
from chat.models import Conversation, Message
from .models import APNSDevice, GCMDevice


class DeviceAdmin(admin.ModelAdmin):
    list_display = ("__unicode__", "device_id", "user", "active")
    search_fields = ("name", "device_id", "user__username")
    list_filter = ("active", )
    actions = ("sendTestChatNotification", "send_message", "send_bulk_message", "enable", "disable")

    def send_message(self, request, queryset):
        ret = []
        errors = []
        r = ""
        for device in queryset:
            try:
                r = device.send_message("Test single notification")
            except Exception as e:
                errors.append(str(e))
            if r:
                ret.append(r)
        if errors:
            self.message_user(request, _("Some messages could not be processed: %r" % ("\n".join(errors))))
        if ret:
            self.message_user(request, _("All messages were sent: %s" % ("\n".join(ret))))

    send_message.short_description = _("Send test message")

    def send_bulk_message(self, request, queryset):
        r = queryset.send_message("Test bulk notification")
        self.message_user(request, _("All messages were sent: %s" % (r)))

    send_bulk_message.short_description = _("Send test message in bulk")

    def sendTestChatNotification(self, request, queryset):
        if settings.DEBUG:
            for device in queryset:
                userProfile = device.user

                conversation = Conversation.objects.filter(members__in=userProfile).first()

                if conversation:
                    for member in conversation.members.all():
                        if member is not userProfile:
                            friendProfile = member
                            break

                    message = Message.objects.create(conversation=conversation, userProfile=friendProfile,
                                                     text="Test Chat Message")
                    sendChatNotifications(message)

            self.message_user(request, _("Notifications sent"))
        else:
            self.message_user(request, _("Must be in DEBUG mode to use this"))

    sendTestChatNotification.short_description = _("Send a chat message notification")

    def enable(self, request, queryset):
        queryset.update(is_active=True)

    enable.short_description = _("Enable selected devices")

    def disable(self, request, queryset):
        queryset.update(is_active=False)

    disable.short_description = _("Disable selected devices")


admin.site.register(APNSDevice, DeviceAdmin)
admin.site.register(GCMDevice, DeviceAdmin)
