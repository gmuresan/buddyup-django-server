from django.contrib import admin
from status.models import Status, Location, Poke

class StatusAdmin(admin.ModelAdmin):
    list_display = ('text', 'user')
    list_display_links = ('user',)

admin.site.register(Status, StatusAdmin)
admin.site.register(Location)
admin.site.register(Poke)
