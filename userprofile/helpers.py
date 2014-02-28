
def getUserProfileDetailsJson(user):
    details = dict()

    details['userid'] = user.id
    details['firstname'] = user.user.first_name
    details['lastname'] = user.user.last_name
    details['facebookid'] = user.facebookUID

    return details