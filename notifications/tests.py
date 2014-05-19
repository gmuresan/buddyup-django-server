import datetime
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.test import TestCase, Client
from notifications.models import APNSDevice, PushNotifications
from notifications.push_notifications import DATETIME_FORMAT
from notifications.tasks import sendStatusMessageNotificationTask
from status.models import Location, Status, StatusMessage
from userprofile.models import UserProfile, Group


class APNSTests(TestCase):
    def setUp(self):
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user = UserProfile.objects.create(user=user1)

        friend = User.objects.create(username='friend', password='0', email='friend')
        self.friend = UserProfile.objects.create(user=friend)

        self.user.friends.add(self.friend)
        self.friend.friends.add(self.user)

        lat = 42.341560
        lng = -83.501783
        address = '46894 spinning wheel'
        city = 'canton'
        state = 'MI'
        venue = "My house"
        expirationDate = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

        location = Location.objects.create(lng=lng, lat=lat, point=Point(lng, lat), city=city, state=state, venue=venue,
                                           address=address)

        self.status = Status.objects.create(user=self.friend, expires=expirationDate, text='Hang out1',
                                            location=location)

        APNSDevice.objects.create(user=self.friend, registration_id='87141249849018940814')

    def testLongStatusMessagePushNotification(self):
        print("long status message push notification")
        statusMessage = StatusMessage.objects.create(status=self.status, user=self.user,
                                                     text='really long message really long message really long message '
                                                          'really long message really long message really long message '
                                                          'really long message really long message really long message '
                                                          'really long message really long message really long message ')
        pushNotification = PushNotifications.objects.create(message=statusMessage, sendingUser=statusMessage.user,
                                                            pushNotificationType=PushNotifications.PUSH_NOTIF_STATUS_MESSAGE,
                                                            status=self.status)
        pushNotification.receivingUsers.add(self.friend)

        sendStatusMessageNotificationTask(pushNotification)
