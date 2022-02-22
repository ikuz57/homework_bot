class TokenError(Exception):
    pass


class ApiError(Exception):
    def __init__(self, text):
        self.txt = text


class NotListError(Exception):
    def __init__(self, text):
        self.txt = text


class StatusKeyError(Exception):
    def __init__(self, text):
        self.txt = text
