import passlib.hash
import random
import six

password_hash = passlib.hash.sha256_crypt

def crypt(password):
    if isinstance(password, six.text_type):
        password_8bit = password.encode('UTF-8')
    else:
        password_8bit = password

    rv = password_hash.encrypt(password_8bit)
    if not isinstance(rv, six.text_type):
        rv = rv.decode('UTF-8')

    return rv

def verify(password, hash):
    if isinstance(password, six.text_type):
        password_8bit = password.encode('UTF-8')
    else:
        password_8bit = password

    return password_hash.verify(password_8bit, hash)
