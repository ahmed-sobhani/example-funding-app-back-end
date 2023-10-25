from random import randint


def generate_verify_code(user):
    verify_code = str(randint(10000, 99999))
    user.set_verify_code(verify_code)
    return verify_code
