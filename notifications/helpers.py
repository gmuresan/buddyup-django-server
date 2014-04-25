import datetime
from django.db.models import Q
from api.helpers import DATETIME_FORMAT
from notifications.models import Notification

MAX_NOTIFICATION_AGE_DAYS = 5


def getNotificationsJson(user, since=None):
    notifications = Notification.objects.filter(users=user)
    notifications = notifications.filter(Q(status__isnull=True) | Q(status__deleted=False))
    if since is not None:
        notifications = notifications.filter(date__gt=since)
    else:
        threeDaysAgo = datetime.datetime.now() - datetime.timedelta(days=MAX_NOTIFICATION_AGE_DAYS)
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

        json['text'] = str(notif)
        json['date'] = notif.date.strftime(DATETIME_FORMAT)
        json['notificationid'] = notif.id

        json['type'] = notif.notificationType

        notifs.append(json)

    return notifs



