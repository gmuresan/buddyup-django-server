"""
Apple Push Notification Service
Documentation is available on the iOS Developer Library:
https://developer.apple.com/library/ios/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Chapters/ApplePushService.html
"""

import json
import pdb
import ssl
import struct
from binascii import unhexlify
from socket import socket
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from . import NotificationError
from .settings import PUSH_NOTIFICATIONS_SETTINGS as SETTINGS


class APNSError(NotificationError):
    pass


class APNSDataOverflow(APNSError):
    pass


APNS_MAX_NOTIFICATION_SIZE = 256


def _apns_create_socket():
    sock = socket()
    certfile = SETTINGS.get("APNS_CERTIFICATE")
    if not certfile:
        raise ImproperlyConfigured(
            'You need to set PUSH_NOTIFICATIONS_SETTINGS["APNS_CERTIFICATE"] to send messages through APNS.'
        )

    try:
        f = open(certfile, "r")
        f.read()
        f.close()
    except Exception as e:
        raise ImproperlyConfigured("The APNS certificate file at %r is not readable: %s" % (certfile, e))

    sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv3, certfile=certfile)
    sock.connect((SETTINGS["APNS_HOST"], SETTINGS["APNS_PORT"]))

    return sock


def _apns_pack_message(token, data):
    format = "!cH32sH%ds" % (len(data))
    return struct.pack(format, b"\0", 32, unhexlify(token), len(data), data.encode('UTF-8'))


def _apns_send(token, alert, badge=0, sound="chime", content_available=False, action_loc_key=None, loc_key=None,
               loc_args=[], extra={}, socket=None):
    data = {}

    if action_loc_key or loc_key or loc_args:
        alert = {"body": alert}
        if action_loc_key:
            alert["action-loc-key"] = action_loc_key
        if loc_key:
            alert["loc-key"] = loc_key
        if loc_args:
            alert["loc-args"] = loc_args

    data["alert"] = alert

    if badge:
        data["badge"] = badge

    if sound:
        data["sound"] = sound

    if content_available:
        data["content-available"] = 1

    data.update(extra)

    # convert to json, avoiding unnecessary whitespace with separators
    payload = json.dumps({"aps": data}, separators=(",", ":"))

    numBytes = len(payload)
    if numBytes > APNS_MAX_NOTIFICATION_SIZE:
        overflow = numBytes - APNS_MAX_NOTIFICATION_SIZE + 3
        notificationText = data['alert']
        shortenedText = notificationText[:overflow*-1]
        shortenedText += "..."
        data['alert'] = shortenedText
        payload = json.dumps({"aps": data}, separators=(",", ":"))

        if len(payload) > APNS_MAX_NOTIFICATION_SIZE:
            raise APNSDataOverflow("Notification body cannot exceed %i bytes" % APNS_MAX_NOTIFICATION_SIZE)

    data = _apns_pack_message(token, payload)

    if socket:
        socket.write(data)
        #data = socket.recv(4096)
        #print "received message:", data
    else:
        socket = _apns_create_socket()
        socket.write(data)
        socket.close()


def apns_send_message(registration_id, data, **kwargs):
    """
	Sends an APNS notification to a single registration_id.
	This will send the notification as form data.
	If sending multiple notifications, it is more efficient to use
	apns_send_bulk_message()
	Note that \a data should always be a string.
	"""

    return _apns_send(registration_id, data, **kwargs)


def apns_send_bulk_message(registration_ids, data, **kwargs):
    """
	Sends an APNS notification to one or more registration_ids.
	The registration_ids argument needs to be a list.
	"""
    socket = _apns_create_socket()
    for registration_id in registration_ids:
        _apns_send(registration_id, data, socket=socket, **kwargs)

    socket.close()
