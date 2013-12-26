import thread
from push_notifications.models import GCMDevice, APNSDevice


def sendChatNotifications(message):
    thread.start_new_thread(sendChatNotificationsSynchronous, (message,))


def sendChatNotificationsSynchronous(message):
    conversation = message.conversation
    userProfile = message.user

    androidDevices = GCMDevice.objects.filter(user__in=conversation.members.exclude(pk=userProfile.pk))
    iosDevices = APNSDevice.objects.filter(user__in=conversation.members.exclude(pk=userProfile.pk))

    messageContents = {'message': message.text, 'type': 'chat', 'id': conversation.id}

    androidResponse = androidDevices.send_message(messageContents)
    iosResponse = iosDevices.send_message(messageContents)

    return androidResponse, iosResponse