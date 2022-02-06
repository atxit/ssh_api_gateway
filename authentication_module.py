static_user_dict = {'admin': 'cisco_gw'}


def login(username, password):
    if username not in list(static_user_dict.keys()):
        response = {'response': 'Username does not match'}
        response_code = 401
        proceed = False
    elif static_user_dict.get(username) != password:
        response = {'response': 'Password does not match'}
        response_code = 401
        proceed = False
    else:
        response = {}
        response_code = None
        proceed = True
    return response, response_code, proceed
