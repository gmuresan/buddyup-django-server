from django.contrib import admin
from status.models import Status, Location, Poke

class StatusAdmin(admin.ModelAdmin):
    list_display = ('text', 'user', 'starts', 'expires', 'location', 'attendingCount')

    def attendingCount(self, obj):
        return obj.attending.count()

admin.site.register(Status, StatusAdmin)
admin.site.register(Location)
admin.site.register(Poke)
