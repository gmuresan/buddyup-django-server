import pdb
import thread
from django.contrib.auth.models import User
from push_notifications.models import GCMDevice, APNSDevice


def sendPokeNotifcation(pokeObj):
    thread.start_new_thread(sendPokeNotifcation, (pokeObj, ))


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
