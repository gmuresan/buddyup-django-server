from concurrent.futures import ThreadPoolExecutor
import pdb
import _thread as thread
import datetime
from django.contrib.auth.models import User
from chat.models import Message
from notifications.models import GCMDevice, APNSDevice, PushNotifications
from notifications.tasks import handlePushNotification
from status.helpers import isStatusVisibleToUser
from status.models import StatusMessage, Status
from userprofile.models import UserProfile, Group
from celery import Celery

DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S'  # 06-01-2013 13:12

MAX_POOL_WORKERS = 10

THREAD_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_POOL_WORKERS)


def sendFavoritesStatusPushNotification(status):
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
    if isCreated:
        pushNotification.receivingUsers.add(*usersToNotify)
        handlePushNotification.delay(pushNotification.id)

    return usersToNotify


def sendAttendingStatusPushNotification(status, attendingUser):

    pushNotification, created = PushNotifications.objects.get_or_create(status=status,
                                                         pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_MEMBERS_ADDED,
                                                         sendingUser=attendingUser)
    if created:
        pushNotification.receivingUsers.add(status.user)
        handlePushNotification.delay(pushNotification.id)


def sendInvitedToStatusNotification(status, invitingUser, invitedUsers):
    for user in invitedUsers:
        sendNotification = False
        try:
            pushNotification = PushNotifications.objects.get(status=status,
                                                             pushNotificationType=PushNotifications.PUSH_NOTIF_INVITED,
                                                             receivingUsers=user, sendingUser=invitingUser)
            timeDifference = pushNotification.date - datetime.datetime.now()
            if timeDifference.total_seconds() < 30 * 60:
                pushNotification.date = datetime.datetime.now()
                sendNotification = True

        except PushNotifications.DoesNotExist:
            pushNotification = PushNotifications.objects.create(sendingUser=invitingUser,
                                                                pushNotificationType=PushNotifications.PUSH_NOTIF_INVITED,
                                                                status=status)
            pushNotification.receivingUsers.add(user)
            sendNotification = True

        if sendNotification:
            handlePushNotification.delay(pushNotification.id)


def sendStatusMessageNotification(message):
    pushNotification, isCreated = PushNotifications.objects.get_or_create(message=message,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_MESSAGE,
                                                                          sendingUser=message.user)
    if isCreated:
        pushNotification.receivingUsers.add(*message.status.attending.all().exclude(pk=message.user.pk))
        handlePushNotification.delay(pushNotification.id)


def sendDeleteStatusNotfication(status):
    pushNotification, isCreated = PushNotifications.objects.get_or_create(status=status,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_DELETED,
                                                                          sendingUser=status.user)

    if isCreated:
        pushNotification.receivingUsers.add(*status.attending.all().exclude(pk=status.user.pk))
        handlePushNotification.delay(pushNotification.id)


def sendEditStatusNotification(status):
    pushNotification, isCreated = PushNotifications.objects.get_or_create(status=status,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_CHANGED,
                                                                          sendingUser=status.user)
    if isCreated:
        pushNotification.receivingUsers.add(*status.attending.all().exclude(pk=status.user.pk))
        handlePushNotification.delay(pushNotification.id)


def sendChatNotifications(message):
    pushNotification, isCreated = PushNotifications.objects.get_or_create(chatMessage=message,
                                                                          pushNotificationType=PushNotifications.PUSH_NOTIF_CHAT,
                                                                          sendingUser=message.user)
    if isCreated:
        pushNotification.receivingUsers.add(*message.conversation.members.all().exclude(pk=message.user.pk))
        handlePushNotification.delay(pushNotification.id)
