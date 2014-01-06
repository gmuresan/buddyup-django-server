from django.conf.urls import patterns, url, include
from api.facebookGraphObjects import fbObjectStatus
from userprofile.api_functions import *
from chat.api_functions import *
from status.api_functions import *

urlpatterns = patterns('',
                       url(r'^/', include('userprofile.urls')),
                       url(r'^/', include('chat.urls')),
                       url(r'^/', include('status.urls')),


)
