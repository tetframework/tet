def exporter():
    """
    Create an easy export decorator with __all__

    :return: tuple export, __all__, to be set in the module
    """

    all_ = []

    def decorator(obj):
        all_.append(obj.__name__)
        return obj
    return decorator, all_
