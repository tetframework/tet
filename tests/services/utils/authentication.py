def get_cookie(cookiejar, name):
    founded_cookie = [cookie for cookie in cookiejar if cookie.name == name]
    return founded_cookie[0].value if founded_cookie else None
