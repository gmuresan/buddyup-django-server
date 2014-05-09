from concurrent.futures import ThreadPoolExecutor
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

MAX_POOL_WORKERS = 10


THREAD_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_POOL_WORKERS)


def sendFavoritesStatusPushNotification(statusId):
    THREAD_EXECUTOR.submit(sendFavoritesStatusPushNotificationSynchronous, statusId)
    #thread.start_new_thread(sendFavoritesStatusPushNotificationSynchronous, (statusId, ))


def sendFavoritesStatusPushNotificationSynchronous(statusId):
    try:
        status = Status.getStatus(statusId)
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

    pushNotification, isCreated = PushNotifications.objects.get_or_create(status=status,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_FAVORITES,
                                                                          sendingUser=status.user)
    pushNotification.receivingUsers.add(*usersToNotify)

    messageContents = str(pushNotification)
    extra = {'id': status.id, 'statusid': status.id, 'type': 'statuspost', 'userid': status.user.id,
             'date': datetime.datetime.now().strftime(DATETIME_FORMAT)}

    androidDevices = GCMDevice.objects.filter(user__in=usersToNotify)
    iosDevices = APNSDevice.objects.filter(user__in=usersToNotify)

    androidResponse = androidDevices.send_message(messageContents, extra=extra)
    iosResponse = iosDevices.send_message(messageContents, extra=extra)

    return usersToNotify


def sendAttendingStatusPushNotification(statusId, attendingUserId):
    THREAD_EXECUTOR.submit(sendAttendingStatusPushNotificationSynchronous, statusId, attendingUserId)
    #thread.start_new_thread(sendAttendingStatusPushNotificationSynchronous, (statusId, attendingUserId))


def sendAttendingStatusPushNotificationSynchronous(statusId, attendingUserId):
    try:
        status = Status.getStatus(statusId)
    except Status.DoesNotExist:
        return None, None

    try:
        attendingUser = UserProfile.getUser(attendingUserId)
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
    THREAD_EXECUTOR.submit(sendInvitedToStatusNotificationSynchronous, statusId, invitingUserId, invitedUserIds)
    # thread.start_new_thread(sendInvitedToStatusNotificationSynchronous, (statusId, invitingUserId, invitedUserIds))


def sendInvitedToStatusNotificationSynchronous(statusId, invitingUserId, invitedUserIds):
    try:
        invitingUser = UserProfile.getUser(invitingUserId)
        invitedUsers = UserProfile.objects.filter(pk__in=invitedUserIds)

    except UserProfile.DoesNotExist:
        return None, None

    try:
        status = Status.getStatus(statusId)
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
    THREAD_EXECUTOR.submit(sendStatusMessageNotificationSynchronous, messageId)
    #thread.start_new_thread(sendStatusMessageNotificationSynchronous, (messageId, ))


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
    THREAD_EXECUTOR.submit(sendDeleteStatusNotficationSynchronous, statusId)
    #thread.start_new_thread(sendDeleteStatusNotficationSynchronous, (statusId, ))


def sendDeleteStatusNotficationSynchronous(statusId):
    try:
        status = Status.getStatus(statusId)
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
    THREAD_EXECUTOR.submit(sendEditStatusNotificationSynchronous, statusId)
    #thread.start_new_thread(sendEditStatusNotificationSynchronous, (statusId, ))


def sendEditStatusNotificationSynchronous(statusId):
    try:
        status = Status.getStatus(statusId)
    except Status.DoesNotExist:
        return None, None

    pushNotification, isCreated = PushNotifications.objects.get_or_create(status=status,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_CHANGED,
                                                                          sendingUser=status.user)

    try:
        audience = status.attending.all().exclude(pk=status.user.pk)
        pushNotification.receivingUsers.add(*audience)

        messageContents = str(pushNotification)

        extra = {'id': status.id, 'statusid': status.id, 'type': 'statusedited'}

        androidDevices = GCMDevice.objects.filter(user__in=audience)
        iosDevices = APNSDevice.objects.filter(user__in=audience)

        androidResponse = androidDevices.send_message(messageContents, extra=extra)
        iosResponse = iosDevices.send_message(messageContents, extra=extra)

        return androidResponse, iosResponse

    except User.DoesNotExist:
        return None, None


def sendPokeNotification(pokeObj):
    THREAD_EXECUTOR.submit(sendPokeNotificationSynchronous, pokeObj)
    #thread.start_new_thread(sendPokeNotificationSynchronous, (pokeObj, ))


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
    THREAD_EXECUTOR.submit(sendChatNotificationsSynchronous, messageId)
    #thread.start_new_thread(sendChatNotificationsSynchronous, (messageId, ))


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

