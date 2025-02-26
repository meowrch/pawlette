class ThemeNotFound(Exception):
    def __init__(self, theme_name: str, extra_info: dict = None) -> None:
        message = f'The topic titled "{theme_name}" was not found.'
        super().__init__(message)

        if extra_info:
            self.extra_info = extra_info
