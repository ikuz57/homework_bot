# вот думаю, а может и не надо было этого
class token_error(Exception):
    pass


class api_error(Exception):
    def __init__(self, text):
        self.txt = text


class parse_error(Exception):
    def __init__(self, text):
        self.txt = text


class status_key_error(Exception):
    def __init__(self, text):
        self.txt = text
