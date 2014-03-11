import datetime
from django.db.models import Q
from api.helpers import DATETIME_FORMAT
from notifications.models import Notification


def getNotificationsJson(user, since=None):

    notifications = Notification.objects.filter(users=user)
    if since is not None:
        notifications = notifications.filter(date__gt=since)
    else:
        threeDaysAgo = datetime.datetime.now() - datetime.timedelta(days=3)
        notifications = notifications.filter(date__gt=threeDaysAgo)
        now = datetime.datetime.now()
        notifications = notifications.filter(Q(status__isnull=True) | Q(status__expires__gt=now))

    notifs = list()
    for notif in notifications:
        json = dict()

        if notif.initiatingUser:
            json['friendid'] = notif.initiatingUser.id

        if notif.status:
            json['statusid'] = notif.status.id

        json['text'] = unicode(notif)
        json['date'] = notif.date.strftime(DATETIME_FORMAT)
        json['notificationid'] = notif.id

        json['type'] = notif.notificationType

        notifs.append(json)

    return notifs



