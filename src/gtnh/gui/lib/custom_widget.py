from typing import Any


class CustomWidget:
    def __init__(self, text: str) -> None:
        self.label_text = text

    def get_description(self) -> str:
        return self.label_text

    def get_description_size(self) -> int:
        return len(self.label_text)

    def grid(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    def grid_forget(self) -> None:
        raise NotImplementedError

    def configure(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError
