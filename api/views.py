import json

from django.http import HttpResponse


def errorResponse(error, response=None):
    if not response:
        response = dict()

    response['error'] = error
    response['success'] = False
    return HttpResponse(json.dumps(response))












