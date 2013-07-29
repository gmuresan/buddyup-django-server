from django.contrib import admin
from userprofile.models import UserProfile, Group


admin.site.register(UserProfile)
admin.site.register(Group)
