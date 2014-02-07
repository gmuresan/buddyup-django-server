from itertools import chain
import pdb
from notifications.models import Notification


def createFriendJoinedNotification(userProfile):
    notification = Notification.objects.create(notificationType=Notification.NOTIF_FRIEND_JOINED,
                                               initiatingUser=userProfile)
    notification.users.add(*(userProfile.friends.all()))


def createCreateStatusMessageNotification(statusMessage):
    user = statusMessage.user
    status = statusMessage.status
    attending = status.attending.all().exclude(id=user.id)

    notification = Notification.objects.create(notificationType=Notification.NOTIF_STATUS_MESSAGE, initiatingUser=user,
                                               status=status, message=statusMessage)
    notification.users.add(*attending)
    if status.user.id != user.id:
        notification.users.add(status.user)


def createStatusChangedNotification(status):
    attending = status.attending.all().exclude(id=status.user.id)
    invited = status.invited.all().exclude(id=status.user.id)
    notifiedUsers = chain(attending, invited)

    notification = Notification.objects.create(notificationType=Notification.NOTIF_STATUS_CHANGED,
                                               initiatingUser=status.user, status=status)
    notification.users.add(*notifiedUsers)


def createAttendingStatusNotification(status, newAttendingUser):
    attending = status.attending.all().exclude(id=newAttendingUser.id)
    invited = status.invited.all().exclude(id=newAttendingUser.id)
    notifiedUsers = chain(attending, invited)

    notification = Notification.objects.create(notificationType=Notification.NOTIF_STATUS_MEMBERS_ADDED,
                                               initiatingUser=newAttendingUser,
                                               status=status)
    notification.users.add(*notifiedUsers)


def createInvitedToStatusNotification(invitedUsers, invitingUser, status):
    notification = Notification.objects.create(notificationType=Notification.NOTIF_INVITED, initiatingUser=invitingUser,
                                               status=status)
    notification.users.add(*invitedUsers)
