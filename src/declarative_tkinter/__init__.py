__version__ = "0.1.0"

import sys
import tkinter
import tkinter.font

from abc import abstractmethod
from typing import Literal, Final, TypeGuard, overload, NotRequired, Any, Callable, Optional, Self

TkVersion: Final = tkinter.TkVersion
TclVersion: Final = tkinter.TclVersion
PyVersion: Final = sys.version_info
Platform: Final = sys.platform

if TkVersion < 9.0:
  raise RuntimeError("This program requires Tk version 9.0 or higher.")
if PyVersion < (3, 14):
  raise RuntimeError("This program requires Python version 3.14 or higher.")

def exit(exitCode: sys._ExitCode):
  sys.exit(exitCode)

def _ismacos() -> bool:
  return sys.platform == "darwin"

def _iswin() -> bool:
  return sys.platform.startswith("win32")

def _clamp(minv: float | int, value: float | int, maxv: float | int, /) -> float | int:
  """ 値を`minv`から`maxv`の範囲に制限します。

  Args:
    minv (float | int): 最小値
    value (float | int): 対象の値
    maxv (float | int): 最大値
  """
  return max(minv, min(maxv, value))

def _executeifcallable(func: Optional[Callable], /, *args: Any, **kwargs: Any) -> Any:
  if func is not None and callable(func):
    return func(*args, **kwargs)
  return None


class App:
  def __init__(self) -> None:
    self.root = tkinter.Tk()
    self._systray: None | SysTray = None
    self.root.withdraw()
    self._windows: list[Window] = []
    self._menu: Menu | None = None
    self._events: dict[str, list[Callable[[App], Any]]] = {
      "ready": [],
    }

  def quit(self) -> None:
    for window in self._windows:
      flag = window.close()
      if not flag:
        return # interrupt quitting
    self.root.destroy()

  def ready(self) -> None:
    for handler in self._events["ready"]:
      handler(self)
    self.root.mainloop()

  def set_badge(self, count: int | None | str = None) -> None:
    if count is None:
      self.root.eval('wm iconbadge . ""')
    elif count == "!":
      self.root.eval('wm iconbadge . !')
    else:
      if not isinstance(count, int):
        count = int(count)
      self.root.call("wm", "iconbadge", ".", count)

  def notify(self, body: Notification) -> bool:
    if _iswin() and self._systray is None:
      # Please create SysTray first in Windows, but currently it is not implemented
      return False
    else:
      try:
        self.root.call("tk", "sysnotify", *body)
      except tkinter.TclError as error:
        print(error)
        return False
      return True

  def on(self, event_name: str, handler: Callable[[App], Any]) -> None:
    if not callable(handler):
      raise TypeError("handler must be callable")
    if event_name in self._events:
      self._events[event_name].append(handler)
    elif event_name in [
      "tkAboutDialog",
      "tk::mac::ShowPreferences",
      "tk::mac::ShowHelp",
      "tk::mac::Quit",
      "tk::mac::OnHide",
      "tk::mac::OnShow",
      "tk::mac::OpenApplication",
      "tk::mac::ReopenApplication",
      "tk::mac::OpenDocument",
      "tk::mac::PrintDocument",
    ]:
      self.root.createcommand(event_name, lambda: handler(self))
    else:
      raise ValueError(f"Unsupported event name: {event_name} (use app.bind instead)")

  def _register_window(self, window: Window) -> None:
    if self._menu is not None:
      window.window.config(menu = self._menu.menu)
    self._windows.append(window)

  def get_focused_window(self) -> Optional[Window]:
    focused_widget = self.root.focus_get()
    print(focused_widget)
    if focused_widget is None:
      return None
    focused_toplevel = focused_widget.winfo_toplevel()
    for window in self._windows:
      if window.window == focused_toplevel:
        return window
    return None


class Menu:
  def __init__(self, menu: list[MenuItem], /) -> None:
    self.menu = tkinter.Menu()
    self.app: App | None = None
    self.items: list[MenuItem] = menu
    for item in menu:
      item._generate(self, self.menu)

  def __getitem__(self, index: int) -> MenuItem:
    return self.items[index]

  def __len__(self) -> int:
    return len(self.items)


class MenuItem:
  def __init__(self) -> None:
    self.app: App | None = None

  @abstractmethod
  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    self.parent = parent
    self.rootmenu = rootmenu

  @abstractmethod
  def _insert_to_parent(self, rootmenu: Menu, parent: tkinter.Menu, index: int) -> None:
    self.parent = parent
    self.rootmenu = rootmenu

  def _get_app(self) -> App:
    if self.rootmenu.app is not None:
      return self.rootmenu.app
    raise RuntimeError("Menu is not associated with App")


class MenuSubmenu(MenuItem):
  def __init__(self,
    label: str,
    /, *,
    items: list[MenuItem],
    font: Optional[tkinter.font._FontDescription] = None
  ) -> None:
    super().__init__()
    self.label = label
    self.items = items
    self.font = font
    self.menu: tkinter.Menu | None = None

  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    super()._generate(rootmenu, parent)
    self.menu = tkinter.Menu(parent, tearoff = 0)
    for item in self.items:
      item._generate(rootmenu, self.menu)
    parent.add_cascade(
      label = self.label,
      menu = self.menu,
      font = self.font if self.font is not None else "",
    )

  def insert(self, index: int, item: MenuItem) -> None:
    self.items.insert(index, item)
    if self.menu is not None:
      item._insert_to_parent(self.rootmenu, self.menu, index)

  def change_child_state(self, index: int, state: Literal["normal", "active", "disabled"]) -> None:
    if not isinstance(self.items[index], (MenuButton, MenuCheckbox, MenuRadio)):
      raise TypeError("Only MenuButton, MenuCheckbox, and MenuRadio can change its state")
    if self.menu is None:
      raise RuntimeError("Menu is not generated yet")
    self.menu.entryconfig(index, state = state)

  def __getitem__(self, index: int) -> MenuItem:
    return self.items[index]

  def __len__(self) -> int:
    return len(self.items)

class MenuButton(MenuItem):
  def __init__(
    self,
    label: str,
    /, *,
    click: Optional[Callable[[App], Any]] = None,
    accelerator: Optional[str] = None,
    state: Literal["normal", "active", "disabled"] = "normal",
    font: Optional[tkinter.font._FontDescription] = None,
    image: Optional[tkinter._Image | str] = None,
  ) -> None:
    super().__init__()
    if click is not None and not callable(click):
      raise TypeError("click must be callable")

    self.label = label
    self.click = click
    self.accelerator = accelerator
    self.state: Literal["normal", "active", "disabled"] = state
    self.font = font
    self.image = image

  def _make_kwargs(self) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    kwargs["label"] = self.label
    kwargs["command"] = lambda: _executeifcallable(self.click, self._get_app())
    kwargs["state"] = self.state
    if self.accelerator is not None:
      kwargs["accelerator"] = self.accelerator
    if self.font is not None:
      kwargs["font"] = self.font
    if self.image is not None:
      kwargs["image"] = self.image
      kwargs["compound"] = tkinter.LEFT
    return kwargs

  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    super()._generate(rootmenu, parent)
    parent.add_command(**self._make_kwargs())

  def _insert_to_parent(self, rootmenu: Menu, parent: tkinter.Menu, index: int) -> None:
    super()._insert_to_parent(rootmenu, parent, index)
    parent.insert_command(index, **self._make_kwargs())

class MenuCheckbox(MenuItem):
  def __init__(self,
    label: str,
    /, *,
    click: Optional[Callable[[App], Any]] = None,
    accelerator: Optional[str] = None,
    indicatoron: bool = True,
    state: Literal["normal", "active", "disabled"] = "normal",
    font: Optional[tkinter.font._FontDescription] = None,
    variable: Optional[tkinter.Variable] = None,
    image: Optional[tkinter._Image] = None,
  ) -> None:
    super().__init__()

    self.label = label
    self.click = click
    self.accelerator = accelerator
    self.indicatoron = indicatoron
    self.state: Literal["normal", "active", "disabled"] = state
    self.font = font
    self.variable = variable
    self.image = image

  def _make_kwargs(self) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    kwargs["label"] = self.label
    kwargs["command"] = lambda: _executeifcallable(self.click, self._get_app())
    kwargs["state"] = self.state
    kwargs["indicatoron"] = self.indicatoron
    if self.accelerator is not None:
      kwargs["accelerator"] = self.accelerator
    if self.font is not None:
      kwargs["font"] = self.font
    if self.image is not None:
      kwargs["image"] = self.image
      kwargs["compound"] = tkinter.LEFT
    if self.variable is not None:
      kwargs["variable"] = self.variable
    return kwargs

  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    super()._generate(rootmenu, parent)
    parent.add_checkbutton(**self._make_kwargs())

  def _insert_to_parent(self, rootmenu: Menu, parent: tkinter.Menu, index: int) -> None:
    super()._insert_to_parent(rootmenu, parent, index)
    parent.insert_checkbutton(index, **self._make_kwargs())

class MenuRadio(MenuItem):
  def __init__(
    self,
    label: str,
    /, *,
    click: Optional[Callable[[App], Any]] = None,
    accelerator: Optional[str] = None,
    indicatoron: bool = True,
    state: Literal["normal", "active", "disabled"] = "normal",
    font: Optional[tkinter.font._FontDescription] = None,
    value: Any = None,
    variable: Optional[tkinter.Variable] = None,
    image: Optional[tkinter._Image] = None,
  ) -> None:
    super().__init__()
    self.label = label
    self.click = click
    self.accelerator = accelerator
    self.indicatoron = indicatoron
    self.state: Literal["normal", "active", "disabled"] = state
    self.font = font
    self.value = value
    self.variable = variable
    self.image = image

  def _make_kwargs(self) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    kwargs["label"] = self.label
    kwargs["command"] = lambda: _executeifcallable(self.click, self._get_app())
    kwargs["state"] = self.state
    kwargs["indicatoron"] = self.indicatoron
    if self.accelerator is not None:
      kwargs["accelerator"] = self.accelerator
    if self.font is not None:
      kwargs["font"] = self.font
    if self.image is not None:
      kwargs["image"] = self.image
      kwargs["compound"] = tkinter.LEFT
    if self.variable is not None:
      kwargs["variable"] = self.variable
    if self.value is not None:
      kwargs["value"] = self.value
    return kwargs

  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    super()._generate(rootmenu, parent)
    parent.add_radiobutton(**self._make_kwargs())

  def _insert_to_parent(self, rootmenu: Menu, parent: tkinter.Menu, index: int) -> None:
    super()._insert_to_parent(rootmenu, parent, index)
    parent.insert_radiobutton(index, **self._make_kwargs())

class MenuSeparator(MenuItem):
  def __init__(self) -> None:
    super().__init__()

  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    super()._generate(rootmenu, parent)
    parent.add_separator()

  def _insert_to_parent(self, rootmenu: Menu, parent: tkinter.Menu, index: int) -> None:
    super()._insert_to_parent(rootmenu, parent, index)
    parent.insert_separator(index)


class SysTray:
  def __init__(self) -> None:
    raise NotImplementedError("Sorry")


class Notification:
  def __init__(self, title: str, body: str) -> None:
    self.title = title
    self.body = body
    self._count = 0

  def __iter__(self) -> Self:
    return self

  def __next__(self) -> str:
    self._count += 1
    if self._count == 1:
      return self.title
    elif self._count == 2:
      return self.body
    else:
      self._count = 0
      raise StopIteration


class Window:
  def __init__(self,
    app: App,
    /, *,
    parent: Optional[tkinter.Misc] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    maxsize: Optional[tuple[int, int]] = None,
    minsize: Optional[tuple[int, int]] = None,
    resizable: Optional[tuple[bool, bool]] = None,
    always_on_top: Optional[bool] = None,
    alpha: Optional[float] = None,
    background: Optional[str] = None,
  ) -> None:
    """
    Args:
      app (App): App
      parent (tkinter.Misc, optional): 親ウィンドウ
    """

    self.app = app
    self.parent: tkinter.Misc | None
    self._events: dict[str, list[Callable[[Window], Any]]] = {
      "beforeclose": [],
      "closed": [],
    }

    if parent is not None:
      self.window = tkinter.Toplevel(parent)
      self.parent = parent
    else:
      self.window = tkinter.Toplevel()
      self.parent = None

    self._window_name = "." + self.window.winfo_name()
    if width is not None and height is not None:
      if width <= 0:
        raise ValueError("The window width must be positive")
      if height <= 0:
        raise ValueError("The window height must be positive")
      self.window.geometry(self.__geometry_str(width, height, x, y))

    if maxsize is not None:
      self.window.maxsize(*maxsize)
    if minsize is not None:
      self.window.minsize(*minsize)
    if resizable is not None:
      self.window.resizable(*resizable)

    if always_on_top is not None:
      self.set_topmost(always_on_top)

    if alpha is not None:
      self.set_window_alpha(alpha)

    if background is not None:
      self.set_background_color(background)

    self.window.protocol("WM_DELETE_WINDOW", self.close)
    self.app._register_window(self)

  def on(self, event_name: str, handler: Callable[[Window], Any]) -> None:
    if not callable(handler):
      raise TypeError("handler must be callable")
    if event_name in self._events:
      self._events[event_name].append(handler)
    else:
      raise ValueError(f"Unsupported event name: {event_name} (use window.bind instead)")

  def is_dark_mode(self) -> bool:
    if _ismacos():
      return bool(self.window.attributes("-isdark"))
    raise NotImplementedError("is_dark_mode is only supported on macOS")

  def set_bounce(self, flag: bool) -> None:
    if _ismacos():
      self.window.attributes("-bounce", "1" if flag else "0")
    else:
      raise NotImplementedError("set_bounce is only supported on macOS")

  def get_bounce(self) -> bool:
    if _ismacos():
      return bool(self.window.attributes("-bounce"))
    raise NotImplementedError("get_bounce is only supported on macOS")

  def set_modified_state(self, flag: bool) -> None:
    if _ismacos():
      self.window.attributes("-modified", "1" if flag else "0")
    else:
      raise NotImplementedError("set_modified_state is only supported on macOS")

  def get_modified_state(self) -> bool:
    if _ismacos():
      return bool(self.window.attributes("-modified"))
    raise NotImplementedError("get_modified_state is only supported on macOS")

  def set_window_alpha(self, alpha: float) -> None:
    alpha = _clamp(0.0, alpha, 1.0)
    self.window.attributes("-alpha", alpha)

  def get_window_alpha(self) -> float:
    return float(self.window.attributes("-alpha"))

  def set_fullscreen(self, flag: bool) -> None:
    fullscreen = 1 if flag else 0
    self.window.attributes("-fullscreen", fullscreen)

  def is_fullscreen(self) -> bool:
    return bool(self.window.attributes("-fullscreen"))

  def set_topmost(self, flag: bool) -> None:
    topmost = 1 if flag else 0
    self.window.attributes("-topmost", topmost)

  def is_topmost(self) -> bool:
    return bool(self.window.attributes("-topmost"))

  def set_appearance_mode(self, mode: Literal["light", "dark"]) -> None:
    if _ismacos():
      if mode == "light":
        self.window.attributes("-appearance", "aqua")
      elif mode == "dark":
        self.window.attributes("-appearance", "darkaqua")
      else:
        raise ValueError('mode must be "light" or "dark"')
    else:
      raise NotImplementedError("set_appearance_mode is only supported on macOS")

  def set_background_color(self, color: str) -> None:
    self.window.configure(background = color)

  def set_menu(self, menu: Menu) -> None:
    menu.app = self.app
    self._menu = menu
    self.window.config(menu = menu.menu)

  def set_geometry(self, *, width: Optional[int] = None, height: Optional[int] = None, x: Optional[int] = None, y: Optional[int] = None) -> None:
    if width is None: width = self.window.winfo_width()
    if height is None: height = self.window.winfo_height()
    if x is None: x = self.window.winfo_x()
    if y is None: y = self.window.winfo_y()
    self.window.geometry(self.__geometry_str(width, height, x, y))

  def __geometry_str(self, width: int, height: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
    if x is not None and y is not None:
      x_str = ("-" if x < 0 else "+") + str(abs(x))
      y_str = ("-" if y < 0 else "+") + str(abs(y))
      return f"{width}x{height}{x_str}{y_str}"
    return f"{width}x{height}"

  def focus(self) -> None:
    self.window.focus()

  def set_title(self, title: str) -> None:
    self.window.title(title)

  def close(self) -> bool:
    for event in self._events["beforeclose"]:
      flag = event(self)
      if flag is not None and not flag:
        return False
    self.app._windows.remove(self)
    self.window.destroy()
    for event in self._events["closed"]:
      event(self)
    return True
