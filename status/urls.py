from django.conf.urls import patterns, url
from status.api_functions import *

urlpatterns = patterns('',

                       url(r'^poke/$', poke, {}, 'pokeAPI'),
                       url(r'^cancelstatus/$', cancelStatus, {}, 'cancelStatusAPI'),
                       url(r'^deletestatus/$', deleteStatus, {}, 'deleteStatusAPI'),

                       url(r'^poststatus/$', postStatus, {}, 'postStatusAPI'),
                       url(r'^deletestatus/$', deleteStatus, {}, 'deleteStatusAPI'),
                       url(r'^getstatuses/$', getStatuses, {}, 'getStatusesAPI'),
                       url(r'^getmystatuses/$', getMyStatuses, {}, 'getMyStatusesAPI'),
                       url(r'^getstatusdetails/$', getStatusDetails, {}, 'getStatusDetailsAPI'),
                       url(r'^poststatusmessage/$', sendStatusMessage, {}, 'postStatusMessageAPI'),
                       url(r'^rsvpstatus/$', rsvpStatus, {}, 'resvpStatusAPI'),

                       )