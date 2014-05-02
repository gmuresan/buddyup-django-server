from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from chat.models import Message
from notifications.fields import UUIDField
from status.models import Status, StatusMessage

from userprofile.models import UserProfile


class Device(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Name"), blank=True, null=True)
    active = models.BooleanField(verbose_name=_("Is active"), default=True,
                                 help_text=_("Inactive devices will not be sent notifications"))
    user = models.ForeignKey(UserProfile, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name or str(self.device_id or "") or "%s for %s" % (
            self.__class__.__name__, self.user or "unknown user")


class GCMDeviceManager(models.Manager):
    def get_query_set(self):
        return GCMDeviceQuerySet(self.model)


class GCMDeviceQuerySet(models.query.QuerySet):
    def send_message(self, message, extra={}):
        if self:
            from .gcm import gcm_send_bulk_message

            data = {"message": message}
            data.update(extra)
            return gcm_send_bulk_message(
                registration_ids=list(self.values_list("registration_id", flat=True)),
                data=data,
                collapse_key="message"
            )


class GCMDevice(Device):
    # device_id cannot be a reliable primary key as fragmentation between different devices
    # can make it turn out to be null and such:
    # http://android-developers.blogspot.co.uk/2011/03/identifying-app-installations.html
    device_id = UUIDField(verbose_name=_("Device ID"), blank=True, null=True,
                          help_text="ANDROID_ID / TelephonyManager.getDeviceId()")
    registration_id = models.TextField(verbose_name=_("Registration ID"))

    objects = GCMDeviceManager()

    class Meta:
        verbose_name = _("GCM device")

    def send_message(self, message, extra={}):
        from .gcm import gcm_send_message

        data = {"message": message}
        data.update(extra)
        return gcm_send_message(registration_id=self.registration_id, data=data, collapse_key="message")


class APNSDeviceManager(models.Manager):
    def get_query_set(self):
        return APNSDeviceQuerySet(self.model)


class APNSDeviceQuerySet(models.query.QuerySet):
    def send_message(self, message, **kwargs):
        if self:
            from .apns import apns_send_bulk_message

            return apns_send_bulk_message(registration_ids=list(self.values_list("registration_id", flat=True)),
                                          data=message, **kwargs)


class APNSDevice(Device):
    device_id = UUIDField(verbose_name=_("Device ID"), blank=True, null=True,
                          help_text="UDID / UIDevice.identifierForVendor()")
    registration_id = models.CharField(verbose_name=_("Registration ID"), max_length=64, unique=True)

    objects = APNSDeviceManager()

    class Meta:
        verbose_name = _("APNS device")

    def send_message(self, message, **kwargs):
        from .apns import apns_send_message

        return apns_send_message(registration_id=self.registration_id, data=message, **kwargs)


class Notification(models.Model):
    NOTIF_FRIEND_JOINED = 1
    NOTIF_STATUS_MESSAGE = 2
    NOTIF_STATUS_CHANGED = 3
    NOTIF_STATUS_MEMBERS_ADDED = 4
    NOTIF_INVITED = 5
    NOTIF_DELETED = 6

    NOTIF_TYPE_CHOICES = ((NOTIF_FRIEND_JOINED, "Friend Joined"), (NOTIF_INVITED, "Invited To Activity"),
                          (NOTIF_STATUS_CHANGED, "Activity Changed"), (NOTIF_STATUS_MESSAGE, "New Activity Message"),
                          (NOTIF_STATUS_MEMBERS_ADDED, "Activity Members Added"), (NOTIF_DELETED, "Activity Deleted"))

    users = models.ManyToManyField(UserProfile, related_name='notifications', null=True, blank=True)
    initiatingUser = models.ForeignKey(UserProfile, related_name='notificationsInitiated')
    date = models.DateTimeField(auto_now=True)
    status = models.ForeignKey(Status, null=True, blank=True)
    message = models.ForeignKey(StatusMessage, null=True, blank=True)
    notificationType = models.IntegerField(choices=NOTIF_TYPE_CHOICES, db_index=True)

    def __str__(self):
        if self.notificationType == self.NOTIF_FRIEND_JOINED:
            return "{} {} has joined BuddyUp".format(self.initiatingUser.user.first_name,
                                                     self.initiatingUser.user.last_name)

        elif self.notificationType == self.NOTIF_STATUS_MEMBERS_ADDED:
            return "{} {} is now attending {}".format(self.initiatingUser.user.first_name,
                                                      self.initiatingUser.user.last_name, str(self.status.text))

        elif self.notificationType == self.NOTIF_STATUS_MESSAGE:
            return "{} {} commented on {}: {}".format(self.initiatingUser.user.first_name,
                                                      self.initiatingUser.user.last_name, str(self.status.text),
                                                      str(self.message.text))

        elif self.notificationType == self.NOTIF_STATUS_CHANGED:
            return "{} {} has made changes to their activity {}".format(self.initiatingUser.user.first_name,
                                                                        self.initiatingUser.user.last_name,
                                                                        str(self.status.text))

        elif self.notificationType == self.NOTIF_INVITED:
            return "You have been invited to {} by {} {}".format(str(self.status.text),
                                                                 self.initiatingUser.user.first_name,
                                                                 self.initiatingUser.user.last_name)

        elif self.notificationType == self.NOTIF_DELETED:
            return "{} {} has deleted {}".format(self.initiatingUser.user.first_name,
                                                 self.initiatingUser.user.last_name,
                                                 self.status.text)

class PushNotifications(models.Model):

    PUSH_NOTIF_STATUS_MESSAGE = 1
    PUSH_NOTIF_STATUS_CHANGED = 2
    PUSH_NOTIF_STATUS_MEMBERS_ADDED = 3
    PUSH_NOTIF_INVITED = 4
    PUSH_NOTIF_DELETED = 5
    PUSH_NOTIF_CHAT = 6

    PUSH_NOTIF_TYPE_CHOICES = ((PUSH_NOTIF_STATUS_MESSAGE, "Push New Activity Message"),
                               (PUSH_NOTIF_STATUS_CHANGED, "Push Activity Changed"),
                               (PUSH_NOTIF_STATUS_MEMBERS_ADDED, "Push Activity Member Added"),
                               (PUSH_NOTIF_INVITED, "Push Invited To Activity"),
                               (PUSH_NOTIF_DELETED, "Push Activity Deleted"),
                               (PUSH_NOTIF_CHAT, "Push New Chat Message"))

    date = models.DateTimeField(auto_now=True)
    sendingUser = models.ForeignKey(UserProfile)
    receivingUsers = models.ManyToManyField(UserProfile, related_name='pushNotifications')
    pushNotificationType = models.IntegerField(choices=PUSH_NOTIF_TYPE_CHOICES, db_index=True)
    status = models.ForeignKey(Status, null=True, blank=True)
    message = models.ForeignKey(StatusMessage, null=True, blank=True)
    chatMessage = models.ForeignKey(Message, null=True, blank=True)

    def __str__(self):
        if self.pushNotificationType == self.PUSH_NOTIF_STATUS_MESSAGE:
            return self.message.user.user.first_name + " " + self.message.user.user.last_name + " commented on " + \
                          self.message.status.text + " : " + self.message.text

        elif self.pushNotificationType == self.PUSH_NOTIF_STATUS_CHANGED:
            return self.status.user.user.first_name + " " + self.status.user.user.last_name + "has made changes to" + \
                        self.status.status.text

        elif self.pushNotificationType == self.PUSH_NOTIF_STATUS_MEMBERS_ADDED:
            return "{} {} is now attending {}".format(self.sendingUser.user.first_name,
                                                      self.sendingUser.user.last_name, str(self.status.text))

        elif self.pushNotificationType == self.PUSH_NOTIF_INVITED:
            return self.sendingUser.user.first_name + " " + self.sendingUser.user.last_name + " invited you to " + self.status.text

        elif self.pushNotificationType == self.PUSH_NOTIF_DELETED:
            return self.status.user.user.first_name + " " + self.status.user.user.last_name + " deleted " + \
                          self.status.text

        elif self.pushNotificationType == self.PUSH_NOTIF_CHAT:
            return self.sendingUser.user.first_name + " " + self.sendingUser.user.last_name + ": " + self.chatMessage.text
