from celery import Celery, shared_task
from django.contrib.auth.models import User
from chat.models import Message
from notifications.models import PushNotifications, GCMDevice, APNSDevice


@shared_task
def handlePushNotification(pushNotificationId):
    try:
        pushNotification = PushNotifications.objects.get(pk=pushNotificationId)
        print(pushNotificationId)
        print(pushNotification)

        if pushNotification.pushNotificationType == PushNotifications.PUSH_NOTIF_CHAT:
            sendChatNotification(pushNotification)
    except PushNotifications.DoesNotExist:
        pass


def sendChatNotification(pushNotification):
    try:
        print("handling chat")

        message = pushNotification.chatMessage
        conversation = message.conversation
        userProfile = message.user

        print(userProfile)

        audience = conversation.members.all()
        audience = audience.exclude(pk=userProfile.pk)

        print(audience)

        pushNotification.receivingUsers.add(*audience)

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        print(iosDevices)

        messageContents = str(pushNotification)
        extra = {'id': conversation.id, 'type': 'chat', 'userid': message.user.id}

        print(messageContents)
        print(extra)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        print(iosResponse)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None