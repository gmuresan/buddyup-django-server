import pdb
import _thread as thread
import datetime
from django.contrib.auth.models import User
from chat.models import Message
from notifications.models import GCMDevice, APNSDevice, PushNotifications
from status.helpers import isStatusVisibleToUser
from status.models import StatusMessage, Status
from userprofile.models import UserProfile, Group

DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S'  # 06-01-2013 13:12


def sendFavoritesStatusPushNotification(statusId):
    thread.start_new_thread(sendFavoritesStatusPushNotificationSynchronous, (statusId, ))


def sendFavoritesStatusPushNotificationSynchronous(statusId):
    try:
        status = Status.objects.get(pk=statusId)
    except Status.DoesNotExist:
        return None

    favoriteGroupsWithThisUser = Group.objects.filter(name=Group.FAVORITES_GROUP_NAME, members=status.user)

    usersWithFavGroups = list()
    for group in favoriteGroupsWithThisUser:
        if group.user.favoritesNotifications and group.user not in usersWithFavGroups:
            usersWithFavGroups.append(group.user)

    usersToNotify = list()
    for user in usersWithFavGroups:
        if isStatusVisibleToUser(status, user):
            usersToNotify.append(user)

    messageContents = status.user.user.first_name + " " + status.user.user.last_name + " posted an activity: " + status.text
    extra = {'id': status.id, 'statusid': status.id, 'type': 'statuspost', 'userid': status.user.id,
             'date': datetime.datetime.now().strftime(DATETIME_FORMAT)}

    androidDevices = GCMDevice.objects.filter(user__in=usersToNotify)
    iosDevices = APNSDevice.objects.filter(user__in=usersToNotify)

    androidResponse = androidDevices.send_message(messageContents, extra=extra)
    iosResponse = iosDevices.send_message(messageContents, extra=extra)

    return usersToNotify


def sendAttendingStatusPushNotification(statusId, attendingUserId):
    thread.start_new_thread(sendAttendingStatusPushNotificationSynchronous, (statusId, attendingUserId))


def sendAttendingStatusPushNotificationSynchronous(statusId, attendingUserId):
    try:
        status = Status.objects.get(pk=statusId)
    except Status.DoesNotExist:
        return None, None

    try:
        attendingUser = UserProfile.objects.get(pk=attendingUserId)
    except UserProfile.DoesNotExist:
        return None, None

    try:
        pushNotification = PushNotifications.objects.get(status=status,
                                                         pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_MEMBERS_ADDED,
                                                         sendingUser=attendingUser)
    except PushNotifications.DoesNotExist:
        pushNotification = PushNotifications.objects.create(sendingUser=attendingUser,
                                                            pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_MEMBERS_ADDED,
                                                            status=status)
        pushNotification.receivingUsers.add(status.user)

        try:
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

    return None, None


def sendInvitedToStatusNotification(statusId, invitingUserId, invitedUserIds):
    thread.start_new_thread(sendInvitedToStatusNotificationSynchronous, (statusId, invitingUserId, invitedUserIds))


def sendInvitedToStatusNotificationSynchronous(statusId, invitingUserId, invitedUserIds):
    try:
        invitingUser = UserProfile.objects.get(pk=invitingUserId)
        invitedUsers = UserProfile.objects.filter(pk__in=invitedUserIds)

    except UserProfile.DoesNotExist:
        return None, None

    try:
        status = Status.objects.get(pk=statusId)
    except Status.DoesNotExist:
        return None, None

    invitedUsersCopy = list(invitedUsers)

    for user in invitedUsersCopy:
        try:
            pushNotification = PushNotifications.objects.get(status=status,
                                                             pushNotificationType=PushNotifications.PUSH_NOTIF_INVITED,
                                                             receivingUsers=user, sendingUser=invitingUser)
            invitedUsers = invitedUsers.exclude(pk=user.pk)
        except PushNotifications.DoesNotExist:
            pushNotification = PushNotifications.objects.create(sendingUser=invitingUser,
                                                                pushNotificationType=PushNotifications.PUSH_NOTIF_INVITED,
                                                                status=status)
            pushNotification.receivingUsers.add(user)
    if (len(invitedUsers)):
        try:
            audience = invitedUsers

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
    return None, None


def sendStatusMessageNotification(messageId):
    thread.start_new_thread(sendStatusMessageNotificationSynchronous, (messageId, ))


def sendStatusMessageNotificationSynchronous(messageId):
    try:
        messageObj = StatusMessage.objects.get(pk=messageId)
    except StatusMessage.DoesNotExist:
        return None, None

    pushNotification, isCreated = PushNotifications.objects.get_or_create(message=messageObj,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_MESSAGE,
                                                                          sendingUser=messageObj.user)

    try:
        audience = messageObj.status.attending.all().exclude(pk=messageObj.user.pk)
        pushNotification.receivingUsers.add(*audience)

        messageContents = str(pushNotification)
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


def sendDeleteStatusNotfication(statusId):
    thread.start_new_thread(sendDeleteStatusNotficationSynchronous, (statusId, ))


def sendDeleteStatusNotficationSynchronous(statusId):
    try:
        status = Status.objects.get(pk=statusId)
    except Status.DoesNotExist:
        return None, None

    pushNotification, isCreated = PushNotifications.objects.get_or_create(status=status,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_DELETED,
                                                                          sendingUser=status.user)

    try:
        audience = status.attending.all().exclude(pk=status.user.pk)
        pushNotification.receivingUsers.add(*audience)

        messageContents = str(pushNotification)

        extra = {'id': status.id, 'statusid': status.id}

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse


    except User.DoesNotExist:
        return None, None

def sendEditStatusNotification(statusId):
    thread.start_new_thread(sendEditStatusNotificationSynchronous, (statusId, ))

def sendEditStatusNotificationSynchronous(statusId):
    try:
        status = Status.objects.get(pk=statusId)
    except Status.DoesNotExist:
        return None, None

    pushNotification, isCreated = PushNotifications.objects.get_or_create(status=status,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_CHANGED,
                                                                          sendingUser=status.user)

    try:
        audience = status.attending.all().exclude(pk=status.user.pk)
        pushNotification.receivingUsers.add(*audience)

        messageContents = str(pushNotification)

        extra = {'id': status.id, 'statusid': status.id,  'type': 'statusedited'}

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


def sendChatNotifications(messageId):
    thread.start_new_thread(sendChatNotificationsSynchronous, (messageId, ))


def sendChatNotificationsSynchronous(messageId):
    try:
        message = Message.objects.get(pk=messageId)
        conversation = message.conversation
    except Message.DoesNotExist:
        return None, None

    pushNotification, isCreated = PushNotifications.objects.get_or_create(chatMessage=message,
                                                                      pushNotificationType=PushNotifications.PUSH_NOTIF_CHAT,
                                                                      sendingUser=message.user)

    try:
        userProfile = message.user

        audience = conversation.members.all()
        audience = audience.exclude(pk=userProfile.pk)

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

