from tkinter import Button
from typing import Any


class CustomButton(Button):
    def __init__(self, *args:Any, **kwargs:Any):
        Button.__init__(self, *args, **kwargs)
        self.text = self["text"]