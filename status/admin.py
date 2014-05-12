from django.contrib import admin
from status.models import Status, Location, Poke
from django.core.urlresolvers import reverse

class StatusAdmin(admin.ModelAdmin):
    list_display = ('text', 'user')
    list_select_related = True

    def object_link(self, obj):
        ct = obj.content_type
        url = reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=(obj.id,))
        return '<a href="%s">%s</a>' % (url, obj.id)
    object_link.allow_tags = True

admin.site.register(Status, StatusAdmin)
admin.site.register(Location)
admin.site.register(Poke)
