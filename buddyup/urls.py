from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from buddyup.views import about, tos, privacyPolicy, index

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^home/$', index,{},'index'),
    url(r'^about/$', about, {}, 'about'),
    url(r'^tos/$', tos, {}, 'tos'),
    url(r'^privacypolicy/$', privacyPolicy, {}, 'privacypolicy'),
    url(r'^api/', include('chat.urls')),
    url(r'^api/', include('userprofile.urls')),
    url(r'^api/', include('status.urls')),


    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

)

urlpatterns += staticfiles_urlpatterns()

