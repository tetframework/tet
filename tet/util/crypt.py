import passlib.hash
import random

password_hash = passlib.hash.sha256_crypt

def crypt(password):
    if isinstance(password, str):
        password_8bit = password.encode()
    else:
        password_8bit = password

    rv = password_hash.encrypt(password_8bit)
    if not isinstance(rv, str):
        rv = rv.decode()

    return rv

def verify(password, hash):
    if isinstance(password, str):
        password_8bit = password.encode()
    else:
        password_8bit = password

    return password_hash.verify(password_8bit, hash)
