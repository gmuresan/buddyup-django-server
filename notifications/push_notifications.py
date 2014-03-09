import pdb
import thread
import datetime
from django.contrib.auth.models import User
from notifications.models import GCMDevice, APNSDevice

DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S'  # 06-01-2013 13:12


def sendInvitedToStatusNotification(status, invitingUser, invitedUser):
    thread.start_new_thread(sendInvitedToStatusNotificationSynchronous, (status, invitingUser, invitedUser))


def sendInvitedToStatusNotificationSynchronous(status, invitingUser, invitedUser):
    try:
        audience = invitedUser

        messageContents = invitingUser.user.first_name + " " + invitingUser.user.last_name + " invited you to " + status.text
        extra = {'id': invitingUser.id, 'statusid': status.id, 'type': 'invite',
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

        messageContents = messageObj.user.user.first_name + " " + messageObj.user.user.last_name + \
                          " commented on " + messageObj.status.text + " : " + messageObj.text
        extra = {'id': messageObj.id, 'statusid': messageObj.status.id,
                 'date': messageObj.date.strftime(DATETIME_FORMAT),
                 'text': messageObj.text, 'type': 'statuscomment'}

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

        androidDevices = GCMDevice.objects.filter(user__in=conversation.members.exclude(pk=userProfile.pk))
        iosDevices = APNSDevice.objects.filter(user__in=conversation.members.exclude(pk=userProfile.pk))

        messageContents = userProfile.user.first_name + " " + userProfile.user.last_name + ": " + message.text
        extra = {'id': conversation.id, 'type': 'chat'}

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None
