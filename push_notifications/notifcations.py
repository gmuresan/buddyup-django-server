import pdb
import thread
from django.contrib.auth.models import User
from push_notifications.models import GCMDevice, APNSDevice


def sendChatNotifications(message):
    thread.start_new_thread(sendChatNotificationsSynchronous, (message, ))


def sendChatNotificationsSynchronous(message):
    conversation = message.conversation
    try:
        userProfile = message.user

        androidDevices = GCMDevice.objects.filter(user__in=conversation.members.exclude(pk=userProfile.pk))
        iosDevices = APNSDevice.objects.filter(user__in=conversation.members.exclude(pk=userProfile.pk))

        messageContents = userProfile.user.first_name + " " + userProfile.user.last_name + ": " + message.text
        extra = {'id': conversation.id, 'type': 'chat'}

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse
    except User.DoesNotExist:
        return None, None