from typing import Any
#import pickle


class NotFoundError(Exception):
    def __init__(self, message: str, value: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.value = value

    def __str__(self) -> str:
        if self.value:
            return f'{self.message} (Server response: {self.value})'
        return self.message

    def __reduce__(self) -> tuple[Any, tuple[str, Any]]:
        return self.__class__, (self.message, self.value)


class ModerationError(Exception):
    def __init__(self, chapter: Any, novel: Any, message: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.chapter = chapter
        self.novel = novel

    def __str__(self) -> str:
        return f'Chapter {self.chapter} of Novel {self.novel} under moderation{f" {self.message}" if self.message else ""}'

    def __reduce__(self) -> tuple[Any, tuple[str, Any, Any]]:
        return self.__class__, (self.message, self.chapter, self.novel)


class UnknownApiError(Exception):
    def __init__(self, message: str, code: Any) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f'{self.message}, code {self.code}'

    def __reduce__(self) -> tuple[Any, tuple[str, Any]]:
        return self.__class__, (self.message, self.code)


class MaxRetriesReachedError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f'{self.message}'

    def __reduce__(self) -> tuple[Any, tuple[str]]:
        return self.__class__, (self.message, )


class FilenameTooBigError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f'{self.message}'

    def __reduce__(self) -> tuple[Any, tuple[str]]:
        return self.__class__, (self.message, )


class UnauthorisedError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f'{self.message}'

    def __reduce__(self) -> tuple[Any, tuple[str]]:
        return self.__class__, (self.message, )


class RestrictedError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f'{self.message}'

    def __reduce__(self) -> tuple[Any, tuple[str]]:
        return self.__class__, (self.message, )


