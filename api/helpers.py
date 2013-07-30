DATETIME_FORMAT = '%m-%d-%Y %H:%M'  # 06-01-2013 13:12


def createStatusJsonObject(status):
    statusData = dict()

    statusData['statusid'] = status.id
    statusData['userid'] = status.user_id
    statusData['text'] = status.text
    statusData['datecreated'] = status.date.strftime(DATETIME_FORMAT)
    statusData['dateexpires'] = status.expires.strftime(DATETIME_FORMAT)

    if status.location:
        location = dict()
        location['lat'] = status.location.lat
        location['lng'] = status.location.lng
        location['address'] = status.location.address
        location['city'] = status.location.city
        location['state'] = status.location.state
        location['venue'] = status.location.venue
        statusData['location'] = location

    return statusData