from api.helpers import DATETIME_FORMAT


def getNewStatusMessages(status, lastMessageId):
    messages = status.messages.all()
    if lastMessageId:
        messages = messages.filter(id__gt=lastMessageId)

    messagesJson = list()
    for message in messages:
        messageObj = dict()
        messageObj['id'] = message.id
        messageObj['userid'] = message.user.id
        messageObj['text'] = message.text
        messageObj['date'] = message.date.strftime(DATETIME_FORMAT)

        messagesJson.append(messageObj)

    return messagesJson