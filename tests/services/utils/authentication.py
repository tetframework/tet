def get_cookie(cookiejar, name):
    matching_cookies = [cookie for cookie in cookiejar if cookie.name == name]
    return matching_cookies[0].value if matching_cookies else None
