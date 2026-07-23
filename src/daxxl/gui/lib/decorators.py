import functools
from tkinter.messagebox import showerror
from typing import Any, Awaitable, Callable, TypeVar, Union, cast

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])
DialogText = Union[str, Callable[..., str]]


def with_error_dialog(title: DialogText, message: DialogText) -> Callable[[F], F]:
    """
    Decorator factoring out the try/except/showerror/toggle-recovery boilerplate
    repeated across Window's async callback methods.

    :param title: dialog title, or a callable(self, *args, **kwargs) -> str for
        dynamic titles that depend on the method's arguments/state.
    :param message: dialog message, same rules as title.
    :return: the decorator to apply to an async method of Window.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                resolved_title = title if isinstance(title, str) else title(self, *args, **kwargs)
                resolved_message = message if isinstance(message, str) else message(self, *args, **kwargs)
                showerror(resolved_title, resolved_message)
                self.current_task_reset_callback()
                self.global_reset_callback()
                if not self.toggled:
                    self.trigger_toggle()
                raise e

        return cast(F, wrapper)

    return decorator
