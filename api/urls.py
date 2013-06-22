from django.conf.urls.defaults import patterns, include, url
from api.views import facebookRegister

urlpatterns = patterns('',
                       url(r'^facebookregister/(\w+)/$', facebookRegister),

)
