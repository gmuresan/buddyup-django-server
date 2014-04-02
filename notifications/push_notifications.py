import pdb
import thread
import datetime
from django.contrib.auth.models import User
from notifications.models import GCMDevice, APNSDevice

DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S'  # 06-01-2013 13:12


def sendAttendingStatusPushNotification(status, attendingUser):
    thread.start_new_thread(sendAttendingStatusPushNotificationSynchronous, (status, attendingUser))


def sendAttendingStatusPushNotificationSynchronous(status, attendingUser):
    try:
        messageContents = attendingUser.user.first_name + " " + attendingUser.user.last_name + " is now attending " + \
                          status.text
        extra = {'id': status.id, 'statusid': status.id, 'type': 'attending', 'userid': attendingUser.id,
                 'date': datetime.datetime.now().strftime(DATETIME_FORMAT)}

        androidDevices = GCMDevice.objects.filter(user=status.user)
        iosDevices = APNSDevice.objects.filter(user=status.user)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None


def sendInvitedToStatusNotification(status, invitingUser, invitedUsers):
    thread.start_new_thread(sendInvitedToStatusNotificationSynchronous, (status, invitingUser, invitedUsers))


def sendInvitedToStatusNotificationSynchronous(status, invitingUser, invitedUsers):
    try:
        audience = invitedUsers

        messageContents = invitingUser.user.first_name + " " + invitingUser.user.last_name + " invited you to " + status.text
        extra = {'id': status.id, 'statusid': status.id, 'type': 'invite', 'userid': invitingUser.id,
                 'date': datetime.datetime.now().strftime(DATETIME_FORMAT)}

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None


def sendStatusMessageNotification(messageObj):
    thread.start_new_thread(sendStatusMessageNotificationSynchronous, (messageObj, ))


def sendStatusMessageNotificationSynchronous(messageObj):
    try:
        audience = messageObj.status.attending.exclude(user=messageObj.user)

        messageContents = messageObj.user.user.first_name + " " + messageObj.user.user.last_name + " commented on " + \
                          messageObj.status.text + " : " + messageObj.text
        extra = {'id': messageObj.status.id, 'statusid': messageObj.status.id,
                 'date': messageObj.date.strftime(DATETIME_FORMAT),
                 'text': messageObj.text, 'type': 'statuscomment', 'userid': messageObj.user.id}

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse
    except User.DoesNotExist:
        return None, None


def sendPokeNotifcation(pokeObj):
    thread.start_new_thread(sendPokeNotificationSynchronous, (pokeObj, ))


def sendPokeNotificationSynchronous(pokeObj):
    try:
        pokerUser = pokeObj.sender
        recipientUser = pokeObj.recipient

        androidDevices = GCMDevice.objects.filter(user=recipientUser)
        iosDevices = APNSDevice.objects.filter(user=recipientUser)

        messageContents = pokerUser.user.first_name + " " + pokerUser.user.last_name + " poked you"
        extra = {'id': pokerUser.id, 'type': 'poke'}

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None


def sendChatNotifications(message):
    thread.start_new_thread(sendChatNotificationsSynchronous, (message, ))


def sendChatNotificationsSynchronous(message):
    conversation = message.conversation
    try:
        userProfile = message.user

        audience = conversation.members.all()
        audience = audience.exclude(pk=userProfile.pk)

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        messageContents = userProfile.user.first_name + " " + userProfile.user.last_name + ": " + message.text
        extra = {'id': conversation.id, 'type': 'chat', 'userid': message.user.id}

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None
