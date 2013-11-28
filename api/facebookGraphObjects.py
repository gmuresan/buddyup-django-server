from django.conf import settings
from django.shortcuts import render_to_response
from django.template import Context, RequestContext
from django.template.loader import get_template
from status.models import Status


def fbObjectStatus(request, statusId):

    status = Status.objects.get(pk=statusId)
    fbAppId = settings.FACEBOOK_APP_ID

    return render_to_response('fb_object_status.html', {'status': status, 'fbAppId': fbAppId},
                              context_instance=RequestContext(request))
