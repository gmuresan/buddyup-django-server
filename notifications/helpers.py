from api.helpers import DATETIME_FORMAT
from notifications.models import Notification


def getNotificationsJson(user, since=None):

    notifications = Notification.objects.filter(users=user)
    if since is not None:
        notifications = notifications.filter(date__gt=since)

    notifs = list()
    for notif in notifications:
        json = dict()

        if notif.initiatingUser:
            json['friendid'] = notif.initiatingUser.id

        if notif.status:
            json['statusid'] = notif.status.id

        json['text'] = str(notif)
        json['date'] = notif.date.strftime(DATETIME_FORMAT)
        json['notificationid'] = notif.id

        json['type'] = notif.notificationType

        notifs.append(json)

    return notifs



