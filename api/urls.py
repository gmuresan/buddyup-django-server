from django.conf.urls.defaults import patterns, include, url
from api.views import facebookRegister, postStatus, poke

urlpatterns = patterns('',
                       url(r'^facebookregister/$', facebookRegister),
                       url(r'^poststatus/$', postStatus),
                       url(r'^poke/$', poke),

)
