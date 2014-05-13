import datetime
from celery import Celery, shared_task
from django.contrib.auth.models import User
from chat.models import Message
from notifications.models import PushNotifications, GCMDevice, APNSDevice

DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S'  # 06-01-2013 13:12

@shared_task
def handlePushNotification(pushNotificationId):
    try:
        pushNotification = PushNotifications.objects.get(pk=pushNotificationId)
        pushType = pushNotification.pushNotificationType

        if pushType == PushNotifications.PUSH_NOTIF_CHAT:
            sendChatNotificationTask(pushNotification)

        elif pushType == PushNotifications.PUSH_NOTIF_STATUS_CHANGED:
            sendEditStatusNotificationTask(pushNotification)

        elif pushType == PushNotifications.PUSH_NOTIF_DELETED:
            sendDeleteStatusNotficationTask(pushNotification)

        elif pushType == PushNotifications.PUSH_NOTIF_STATUS_MESSAGE:
            sendStatusMessageNotificationTask(pushNotification)

        elif pushType == PushNotifications.PUSH_NOTIF_INVITED:
            sendInvitedToStatusNotificationTask(pushNotification)

        elif pushType == PushNotifications.PUSH_NOTIF_FAVORITES:
            sendFavoritesStatusPushNotificationTask(pushNotification)

        elif pushType == PushNotifications.PUSH_NOTIF_STATUS_MEMBERS_ADDED:
            sendAttendingStatusPushNotificationTask(pushNotification)

    except PushNotifications.DoesNotExist:
        pass


def sendFavoritesStatusPushNotificationTask(pushNotification):

    status = pushNotification.status
    usersToNotify = pushNotification.receivingUsers.all()

    messageContents = str(pushNotification)
    extra = {'id': status.id, 'statusid': status.id, 'type': 'statuspost', 'userid': status.user.id,
             'date': datetime.datetime.now().strftime(DATETIME_FORMAT)}

    androidDevices = GCMDevice.objects.filter(user__in=usersToNotify)
    iosDevices = APNSDevice.objects.filter(user__in=usersToNotify)

    androidResponse = androidDevices.send_message(messageContents, extra=extra)
    iosResponse = iosDevices.send_message(messageContents, extra=extra)

    return usersToNotify



def sendAttendingStatusPushNotificationTask(pushNotification):

    try:
        status = pushNotification.status
        attendingUser = pushNotification.sendingUser

        messageContents = str(pushNotification)
        extra = {'id': status.id, 'statusid': status.id, 'type': 'attending', 'userid': attendingUser.id,
                 'date': datetime.datetime.now().strftime(DATETIME_FORMAT)}

        androidDevices = GCMDevice.objects.filter(user=status.user)
        iosDevices = APNSDevice.objects.filter(user=status.user)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None


def sendInvitedToStatusNotificationTask(pushNotification):
    try:

        audience = pushNotification.receivingUsers.all()
        status = pushNotification.status
        invitingUser = pushNotification.sendingUser

        messageContents = str(pushNotification)
        extra = {'id': status.id, 'statusid': status.id, 'type': 'invite', 'userid': invitingUser.id,
                 'date': datetime.datetime.now().strftime(DATETIME_FORMAT)}

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None


def sendStatusMessageNotificationTask(pushNotification):
    try:
        message = pushNotification.message
        audience = pushNotification.receivingUsers.all()

        messageContents = str(pushNotification)
        extra = {'id': message.status.id, 'statusid': message.status.id,
                 'date': message.date.strftime(DATETIME_FORMAT),
                 'text': message.text, 'type': 'statuscomment', 'userid': message.user.id}

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse
    except User.DoesNotExist:
        return None, None



def sendChatNotificationTask(pushNotification):
    try:
        message = pushNotification.chatMessage
        conversation = message.conversation
        userProfile = message.user

        audience = pushNotification.receivingUsers.all()

        pushNotification.receivingUsers.add(*audience)

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        messageContents = str(pushNotification)
        extra = {'id': conversation.id, 'type': 'chat', 'userid': message.user.id}

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None


def sendEditStatusNotificationTask(pushNotification):

    try:
        status = pushNotification.status

        audience = pushNotification.receivingUsers.all()

        messageContents = str(pushNotification)

        extra = {'id': status.id, 'statusid': status.id, 'type': 'statusedited'}

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None


def sendDeleteStatusNotficationTask(pushNotification):

    try:
        status = pushNotification.status
        audience = pushNotification.receivingUsers.all()

        messageContents = str(pushNotification)

        extra = {'id': status.id, 'statusid': status.id}

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None
