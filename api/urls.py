from django.conf.urls.defaults import patterns, include, url
from api.views import facebookRegister, postStatus

urlpatterns = patterns('',
                       url(r'^facebookregister/$', facebookRegister),
                       url(r'^poststatus/$', postStatus),

)
