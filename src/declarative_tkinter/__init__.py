__version__ = "0.1.1"

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
  """ Exit the application with the given exit code.

  Args:
    exitCode (sys._ExitCode): The exit code to exit with. It can be an integer or a string. If it is a string, it will be printed to the standard error before exiting. The exit code will be 0 if the string is empty, and 1 otherwise.

  """
  sys.exit(exitCode)

def _ismacos() -> bool:
  """ Check if the current platform is macOS.

  Returns:
    bool: True if the current platform is macOS, False otherwise.

  """
  return sys.platform == "darwin"

def _iswin() -> bool:
  """ Check if the current platform is Windows.

  Returns:
    bool: True if the current platform is Windows, False otherwise.

  """
  return sys.platform.startswith("win32")

def _clamp(minv: float | int, value: float | int, maxv: float | int, /) -> float | int:
  """ Clamp the value between the minimum and maximum values.

  Args:
    minv (float | int): The minimum value
    value (float | int): The value to clamp
    maxv (float | int): The maximum value

  Returns:
    float | int: The clamped value
  """
  return max(minv, min(maxv, value))

def _executeifcallable(func: Optional[Callable], /, *args: Any, **kwargs: Any) -> Any:
  """ Execute the function if it is callable.

  Args:
    func (Optional[Callable]): The function to execute
    *args: The arguments to pass to the function
    **kwargs: The keyword arguments to pass to the function

  Returns:
    Any: The return value of the function, or None if it is not callable
  """

  if func is not None and callable(func):
    return func(*args, **kwargs)
  return None


class App:
  """ The main application class.

  This class is responsible for managing the application lifecycle, including creating windows, handling events, and managing the system tray (if supported).

  Attributes:
    root (tkinter.Tk): The root Tkinter application instance.
    _systray (Optional[SysTray]): The system tray instance, if supported and created.
    _windows (list[Window]): A list of all windows created by the application.
    _menu (Optional[Menu]): The main menu of the application, if set.
    _events (dict[str, list[Callable[[App], Any]]]): A dictionary mapping event names to lists of event handlers for those events.
  """

  def __init__(self) -> None:
    """ Initialize the App instance.

    This constructor creates the root Tkinter application instance, initializes the system tray to None, withdraws the root window (since we will manage windows manually), and initializes the list of windows, menu, and event handlers.
    """
    self.root = tkinter.Tk()
    self._systray: None | SysTray = None
    self.root.withdraw()
    self._windows: list[Window] = []
    self._menu: Menu | None = None
    self._events: dict[str, list[Callable[[App], Any]]] = {
      "ready": [],
    }

  def quit(self) -> None:
    """ Quit the application.

    This method iterates through all windows and attempts to close them. If any window's close event handler returns False, the quitting process is interrupted. If all windows are closed successfully, the root Tkinter application instance is destroyed, effectively quitting the application.
    """
    for window in self._windows:
      flag = window.close()
      if not flag:
        return # interrupt quitting
    self.root.destroy()

  def ready(self) -> None:
    """ Mark the application as ready.

    This method should be called after setting up the application (e.g., creating windows, setting menus, etc.) to indicate that the application is ready to run. It triggers all event handlers registered for the "ready" event and then starts the Tkinter main event loop.
    """
    for handler in self._events["ready"]:
      handler(self)
    self.root.mainloop()

  def set_badge(self, count: int | None | str = None) -> None:
    """ Set the badge count on the application icon.

    This method is used to set a badge count on the application icon, which can be useful for indicating notifications or other status information. The behavior of this method may vary depending on the operating system and desktop environment.

    Args:
      count (int | None | str, optional): The badge count to set. If None, the badge will be cleared. If "!", a special badge (e.g., an exclamation mark) will be shown. If an integer is provided, it will be displayed as the badge count. Defaults to None.
    """
    if count is None:
      self.root.eval('wm iconbadge . ""')
    elif count == "!":
      self.root.eval('wm iconbadge . !')
    else:
      if not isinstance(count, int):
        count = int(count)
      self.root.call("wm", "iconbadge", ".", count)

  def notify(self, body: Notification) -> bool:
    """ Show a system notification.

    This method attempts to show a system notification with the given body. The behavior of this method may vary depending on the operating system and desktop environment. On Windows, it requires a system tray icon to be created first.
    """

    if _iswin() and self._systray is None:
      # Please create SysTray first in Windows, but currently it is not implemented
      raise NotImplementedError("SysTray is not implemented yet, but it is required for notifications on Windows")
      # return False
    else:
      try:
        self.root.call("tk", "sysnotify", *body)
      except tkinter.TclError as error:
        print(error)
        return False
      return True

  def on(self, event_name: str, handler: Callable[[App], Any]) -> None:
    """ Register an event handler for a specific event.

    This method allows you to register a handler function that will be called when a specific event occurs. The supported events include "ready" for the application and various macOS-specific events (e.g., "tkAboutDialog", "tk::mac::ShowPreferences", etc.). For other events, you should use the `bind` method on the relevant window or widget.

    Args:
      event_name (str): The name of the event to register the handler for. Supported events include "ready" and various macOS-specific events.
      handler (Callable[[App], Any]): The function to be called when the event occurs. It should accept a single argument, which will be the App instance.
    """

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
    """ Register a window with the application.

    This method is called by the Window class when a new window is created. It adds the window to the application's list of windows and sets the application's menu for the window if a menu has been defined.

    Args:
      window (Window): The Window instance to register with the application.
    """
    if self._menu is not None:
      window.window.config(menu = self._menu.menu)
    self._windows.append(window)

  def get_focused_window(self) -> Optional[Window]:
    """ Get the currently focused window.

    This method returns the Window instance that is currently focused (i.e., the window that has input focus). If no window is focused, it returns None. The method works by checking the widget that currently has focus and then finding the corresponding Window instance in the application's list of windows.

    Returns:
      Optional[Window]: The currently focused Window instance, or None if no window is focused.
    """
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
  """ The Menu class represents a menu in the application.

  This class is responsible for managing a menu and its items. It allows you to create a menu structure with submenus, buttons, checkboxes, radio buttons, and separators. The Menu class also provides methods for inserting items into the menu and changing the state of child items.
  """

  def __init__(self, menu: list[MenuItem], /) -> None:
    """ Initialize the Menu instance.

    Args:
      menu (list[MenuItem]): A list of MenuItem instances that represent the items in the menu. Each MenuItem can be a submenu, button, checkbox, radio button, or separator. The menu structure will be generated based on this list when the menu is set for a window.
    """

    self.menu = tkinter.Menu()
    self.app: App | None = None
    self.items: list[MenuItem] = menu
    for item in menu:
      item._generate(self, self.menu)

  def __getitem__(self, index: int) -> MenuItem:
    """ Get a menu item by index.

    This method allows you to access a menu item by its index in the menu's item list. It returns the MenuItem instance at the specified index.

    Args:
      index (int): The index of the menu item to retrieve.
    """
    return self.items[index]

  def __len__(self) -> int:
    """ Get the number of items in the menu.

    This method returns the number of items in the menu's item list, which includes all submenus, buttons, checkboxes, radio buttons, and separators.

    Returns:
      int: The number of items in the menu.
    """
    return len(self.items)


class MenuItem:
  """ The MenuItem class represents an item in a menu.

  This is an abstract base class for different types of menu items, such as submenus, buttons, checkboxes, radio buttons, and separators. Each MenuItem subclass must implement the `_generate` method to create the corresponding menu item in the Tkinter menu and the `_insert_to_parent` method to insert the item into a parent menu at a specific index. The MenuItem class also provides a method to get the associated App instance from the root menu.
  """

  def __init__(self) -> None:
    self.app: App | None = None

  @abstractmethod
  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    """ Generate the menu item in the parent menu.

    This method is responsible for creating the menu item in the given parent menu based on the properties of the MenuItem instance. It should be implemented by each subclass to create the appropriate type of menu item (e.g., command, checkbutton, radiobutton, separator, etc.) and add it to the parent menu.

    Args:
      rootmenu (Menu): The root Menu instance that this item belongs to. This can be used to access the App instance and other properties of the menu.
      parent (tkinter.Menu): The parent Tkinter Menu to which this item should be added. This is the menu that will contain this item as a child. The method should add the generated menu item to this parent menu.
    """
    self.parent = parent
    self.rootmenu = rootmenu

  @abstractmethod
  def _insert_to_parent(self, rootmenu: Menu, parent: tkinter.Menu, index: int) -> None:
    """ Insert the menu item into the parent menu at a specific index.

    This method is responsible for inserting the menu item into the given parent menu at the specified index. It should be implemented by each subclass to insert the appropriate type of menu item (e.g., command, checkbutton, radiobutton, separator, etc.) at the correct position in the parent menu.

    Args:
      rootmenu (Menu): The root Menu instance that this item belongs to. This can be used to access the App instance and other properties of the menu.
      parent (tkinter.Menu): The parent Tkinter Menu to which this item should be added. This is the menu that will contain this item as a child. The method should insert the menu item into this parent menu at the specified index.
      index (int): The index at which to insert the menu item in the parent menu. The index is zero-based, and the item will be inserted before the item currently at that index. If the index is equal to the number of items in the parent menu, the item will be added at the end of the menu.
    """
    self.parent = parent
    self.rootmenu = rootmenu

  def _get_app(self) -> App:
    """ Get the associated App instance from the root menu.

    This method retrieves the App instance associated with the root menu of this menu item. It checks if the root menu has an associated App instance and returns it. If the root menu does not have an associated App instance, it raises a RuntimeError.

    Returns:
      App: The App instance associated with the root menu of this menu item.
    """
    if self.rootmenu.app is not None:
      return self.rootmenu.app
    raise RuntimeError("Menu is not associated with App")


class MenuSubmenu(MenuItem):
  """ The MenuSubmenu class represents a submenu in a menu.

  This class is a subclass of MenuItem and represents a submenu that can contain other menu items. It has a label, a list of child menu items, and optional font settings. The MenuSubmenu class implements the `_generate` method to create the submenu in the parent menu and the `_insert_to_parent` method to insert the submenu into a parent menu at a specific index. It also provides methods to insert new items into the submenu and change the state of child items.
  """

  def __init__(self,
    label: str,
    /, *,
    items: list[MenuItem],
    font: Optional[tkinter.font._FontDescription] = None
  ) -> None:
    """ Initialize the MenuSubmenu instance.

    Args:
      label (str): The label of the submenu that will be displayed in the parent menu.
      items (list[MenuItem]): A list of MenuItem instances that represent the items in the submenu. Each MenuItem can be a submenu, button, checkbox, radio button, or separator. The submenu structure will be generated based on this list when the submenu is created in the parent menu.
      font (Optional[tkinter.font._FontDescription], optional): The font to use for the submenu label. This can be a font description string or a tkinter font object. If None, the default font will be used. Defaults to None.
    """
    super().__init__()
    self.label = label
    self.items = items
    self.font = font
    self.menu: tkinter.Menu | None = None

  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    """ Generate the submenu in the parent menu.

    This method creates a new Tkinter Menu for the submenu, generates all child menu items in this submenu, and then adds the submenu to the parent menu with the appropriate label and font settings.

    Args:
      rootmenu (Menu): The root Menu instance that this submenu belongs to. This can be used to access the App instance and other properties of the menu.
      parent (tkinter.Menu): The parent Tkinter Menu to which this submenu should be added. This is the menu that will contain this submenu as a child. The method should add the generated submenu to this parent menu with the appropriate label and font settings.
    """
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
    """ Insert a new menu item into the submenu at a specific index.

    This method inserts a new MenuItem into the submenu's item list at the specified index and updates the generated submenu in the parent menu to reflect this change. If the submenu has already been generated in the parent menu, it will call the `_insert_to_parent` method of the new item to insert it into the parent menu at the correct position.

    Args:
      index (int): The index at which to insert the new menu item in the submenu's item list. The index is zero-based, and the item will be inserted before the item currently at that index. If the index is equal to the number of items in the submenu, the item will be added at the end of the submenu.
      item (MenuItem): The MenuItem instance to insert into the submenu. This can be a submenu, button, checkbox, radio button, or separator. The submenu structure will be updated to include this new item at the specified index.
    """
    self.items.insert(index, item)
    if self.menu is not None:
      item._insert_to_parent(self.rootmenu, self.menu, index)

  def change_child_state(self, index: int, state: Literal["normal", "active", "disabled"]) -> None:
    """ Change the state of a child menu item in the submenu.

    This method changes the state of a child menu item in the submenu at the specified index. The state can be "normal", "active", or "disabled". If the submenu has already been generated in the parent menu, it will call the `entryconfig` method of the Tkinter Menu to update the state of the corresponding menu item in the parent menu.

    Args:
      index (int): The index of the child menu item in the submenu's item list whose state is to be changed. The index is zero-based.
      state (Literal["normal", "active", "disabled"]): The new state to set for the child menu item. It can be "normal" to enable the item, "active" to highlight the item, or "disabled" to disable the item. The method will update the state of the corresponding menu item in the parent menu if the submenu has already been generated.
    """
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
  """ The MenuButton class represents a button item in a menu.

  This class is a subclass of MenuItem and represents a button that can be clicked to perform an action. It has a label, an optional click handler, an optional accelerator key, a state (normal, active, or disabled), an optional font, and an optional image. The MenuButton class implements the `_generate` method to create the button in the parent menu and the `_insert_to_parent` method to insert the button into a parent menu at a specific index. It also provides a method to create the appropriate keyword arguments for creating the button in the Tkinter menu.
  """

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
    """ Initialize the MenuButton instance.

    Args:
      label (str): The label of the button that will be displayed in the menu.
      click (Optional[Callable[[App], Any]], optional): An optional function that will be called when the button is clicked. The function should accept a single argument, which will be the App instance. If None, no action will be performed when the button is clicked. Defaults to None.
      accelerator (Optional[str], optional): An optional string that represents the accelerator key for the button (e.g., "Ctrl+S"). This will be displayed next to the button label in the menu. Defaults to None.
      state (Literal["normal", "active", "disabled"], optional): The initial state of the button. It can be "normal" to enable the button, "active" to highlight the button, or "disabled" to disable the button. Defaults to "normal".
      font (Optional[tkinter.font._FontDescription], optional): The font to use for the button label. This can be a font description string or a tkinter font object. If None, the default font will be used. Defaults to None.
      image (Optional[tkinter._Image | str], optional): An optional image to display next to the button label. This can be a Tkinter PhotoImage or BitmapImage, or a string representing the path to an image file. If a string is provided, it will be loaded as a PhotoImage. If None, no image will be displayed. Defaults to None.
    """
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
    """ Create the keyword arguments for creating the button in the Tkinter menu.

    This method constructs a dictionary of keyword arguments that can be used to create the button in the Tkinter menu. It includes the label, command (which calls the click handler if it is callable), state, accelerator, font, and image (if provided). The image will be displayed to the left of the label if it is provided.

    Returns:
      dict[str, Any]: A dictionary of keyword arguments for creating the button in the Tkinter menu.
    """
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
  """ The MenuCheckbox class represents a checkbox item in a menu.

  This class is a subclass of MenuItem and represents a checkbox that can be toggled on or off. It has a label, an optional click handler, an optional accelerator key, a state (normal, active, or disabled), an optional font, an optional variable to track the checkbox state, and an optional image. The MenuCheckbox class implements the `_generate` method to create the checkbox in the parent menu and the `_insert_to_parent` method to insert the checkbox into a parent menu at a specific index. It also provides a method to create the appropriate keyword arguments for creating the checkbox in the Tkinter menu.
  """

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
    """ Initialize the MenuCheckbox instance.

    Args:
      label (str): The label of the checkbox that will be displayed in the menu.
      click (Optional[Callable[[App], Any]], optional): An optional function that will be called when the checkbox is toggled. The function should accept a single argument, which will be the App instance. If None, no action will be performed when the checkbox is toggled. Defaults to None.
      accelerator (Optional[str], optional): An optional string that represents the accelerator key for the checkbox (e.g., "Ctrl+S"). This will be displayed next to the checkbox label in the menu. Defaults to None.
      indicatoron (bool, optional): A boolean that indicates whether to show the indicator for the checkbox. If True, a checkmark will be shown when the checkbox is checked. If False, no indicator will be shown. Defaults to True.
      state (Literal["normal", "active", "disabled"], optional): The initial state of the checkbox. It can be "normal" to enable the checkbox, "active" to highlight the checkbox, or "disabled" to disable the checkbox. Defaults to "normal".
      font (Optional[tkinter.font._FontDescription], optional): The font to use for the checkbox label. This can be a font description string or a tkinter font object. If None, the default font will be used. Defaults to None.
      variable (Optional[tkinter.Variable], optional): An optional Tkinter Variable (e.g., BooleanVar) that will be associated with the checkbox to track its state. If provided, this variable will be updated automatically when the checkbox is toggled. Defaults to None.
      image (Optional[tkinter._Image], optional): An optional image to display next to the checkbox label. This can be a Tkinter PhotoImage or BitmapImage. If None, no image will be displayed. Defaults to None.
    """
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
    """ Create the keyword arguments for creating the checkbox in the Tkinter menu.

    This method constructs a dictionary of keyword arguments that can be used to create the checkbox in the Tkinter menu. It includes the label, command (which calls the click handler if it is callable), state, indicatoron, accelerator, font, variable, and image (if provided). The image will be displayed to the left of the label if it is provided.

    Returns:
      dict[str, Any]: A dictionary of keyword arguments for creating the checkbox in the Tkinter menu.
    """
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
  """ The MenuRadio class represents a radio button item in a menu.

  This class is a subclass of MenuItem and represents a radio button that can be selected as part of a group of radio buttons. It has a label, an optional click handler, an optional accelerator key, a state (normal, active, or disabled), an optional font, an optional variable to track the selected radio button in the group, an optional value that represents this radio button's value in the group, and an optional image. The MenuRadio class implements the `_generate` method to create the radio button in the parent menu and the `_insert_to_parent` method to insert the radio button into a parent menu at a specific index. It also provides a method to create the appropriate keyword arguments for creating the radio button in the Tkinter menu.
  """

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
    """ Initialize the MenuRadio instance.

    Args:
      label (str): The label of the radio button that will be displayed in the menu.
      click (Optional[Callable[[App], Any]], optional): An optional function that will be called when the radio button is selected. The function should accept a single argument, which will be the App instance. If None, no action will be performed when the radio button is selected. Defaults to None.
      accelerator (Optional[str], optional): An optional string that represents the accelerator key for the radio button (e.g., "Ctrl+S"). This will be displayed next to the radio button label in the menu. Defaults to None.
      indicatoron (bool, optional): A boolean that indicates whether to show the indicator for the radio button. If True, a dot will be shown when the radio button is selected. If False, no indicator will be shown. Defaults to True.
      state (Literal["normal", "active", "disabled"], optional): The initial state of the radio button. It can be "normal" to enable the radio button, "active" to highlight the radio button, or "disabled" to disable the radio button. Defaults to "normal".
      font (Optional[tkinter.font._FontDescription], optional): The font to use for the radio button label. This can be a font description string or a tkinter font object. If None, the default font will be used. Defaults to None.
      value (Any, optional): An optional value that represents this radio button's value in the group of radio buttons. This value will be assigned to the associated variable when this radio button is selected. Defaults to None.
      variable (Optional[tkinter.Variable], optional): An optional Tkinter Variable (e.g., StringVar) that will be associated with the group of radio buttons to track which one is selected. If provided, this variable will be updated automatically with this radio button's value when it is selected. Defaults to None.
      image (Optional[tkinter._Image], optional): An optional image to display next to the radio button label. This can be a Tkinter PhotoImage or BitmapImage. If None, no image will be displayed. Defaults to None.
    """
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
    """ Create the keyword arguments for creating the radio button in the Tkinter menu.

    This method constructs a dictionary of keyword arguments that can be used to create the radio button in the Tkinter menu. It includes the label, command (which calls the click handler if it is callable), state, indicatoron, accelerator, font, variable, value, and image (if provided). The image will be displayed to the left of the label if it is provided.

    Returns:
      dict[str, Any]: A dictionary of keyword arguments for creating the radio button in the Tkinter menu.
    """
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
  """ The MenuSeparator class represents a separator item in a menu.

  This class is a subclass of MenuItem and represents a separator that can be used to visually separate groups of menu items. It does not have a label or any interactive properties. The MenuSeparator class implements the `_generate` method to create the separator in the parent menu and the `_insert_to_parent` method to insert the separator into a parent menu at a specific index.
  """

  def __init__(self) -> None:
    """ Initialize the MenuSeparator instance. """
    super().__init__()

  def _generate(self, rootmenu: Menu, parent: tkinter.Menu) -> None:
    super()._generate(rootmenu, parent)
    parent.add_separator()

  def _insert_to_parent(self, rootmenu: Menu, parent: tkinter.Menu, index: int) -> None:
    super()._insert_to_parent(rootmenu, parent, index)
    parent.insert_separator(index)


class SysTray:
  """ The SysTray class represents a system tray icon for the application.

  This class is responsible for managing a system tray icon, which can be used to show notifications and provide quick access to application functions. The SysTray class is currently not implemented, but it will eventually provide methods for creating a system tray icon, showing notifications from the tray icon, and handling events related to the tray icon.
  """
  def __init__(self) -> None:
    raise NotImplementedError("Sorry")


class Notification:
  """ The Notification class represents a notification that can be shown to the user.

  This class is responsible for managing a notification, which can include a title and a body. The Notification class implements the iterator protocol to allow iterating over the title and body of the notification. This can be useful for showing the notification in different ways or for processing the title and body separately.
  """

  def __init__(self, title: str, body: str) -> None:
    """ Initialize the Notification instance.

    Args:
      title (str): The title of the notification.
      body (str): The body text of the notification.
    """
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
    """ Initialize the Window instance.

    This method creates a new window for the application with the specified properties. It takes various parameters to configure the window's size, position, resizability, always-on-top behavior, transparency, and background color. The method also sets up event handlers for when the window is closed and registers the window with the application.

    Args:
      app (App): The App instance that this window belongs to. This is used to register the window with the application and to access application-level properties and methods.
      parent (Optional[tkinter.Misc], optional): An optional parent widget for this window. If provided, the window will be created as a child of the specified parent widget. If None, the window will be created as a top-level window without a parent. Defaults to None.
      width (Optional[int], optional): The initial width of the window in pixels. If None, the default width will be used. Defaults to None.
      height (Optional[int], optional): The initial height of the window in pixels. If None, the default height will be used. Defaults to None.
      x (Optional[int], optional): The initial x-coordinate of the window's position on the screen. If None, the default x-coordinate will be used. Defaults to None.
      y (Optional[int], optional): The initial y-coordinate of the window's position on the screen. If None, the default y-coordinate will be used. Defaults to None.
      maxsize (Optional[tuple[int, int]], optional): An optional tuple specifying the maximum width and height of the window in pixels. If None, there will be no maximum size constraint on the window. Defaults to None.
      minsize (Optional[tuple[int, int]], optional): An optional tuple specifying the minimum width and height of the window in pixels. If None, there will be no minimum size constraint on the window. Defaults to None.
      resizable (Optional[tuple[bool, bool]], optional): An optional tuple specifying whether the window is resizable in the horizontal and vertical directions. The first element of the tuple indicates whether the window is resizable horizontally, and the second element indicates whether it is resizable vertically. If None, the window will be resizable in both directions by default. Defaults to None.
      always_on_top (Optional[bool], optional): An optional boolean that indicates whether the window should always be on top of other windows. If True, the window will be kept above all other windows. If False or None, the window will have normal stacking behavior. Defaults to None.
      alpha (Optional[float], optional): An optional float value between 0.0 and 1.0 that specifies the initial transparency of the window. A value of 0.0 means fully transparent, and a value of 1.0 means fully opaque. If None, the default opacity will be used. Defaults to None.
      background (Optional[str], optional): An optional string that specifies the initial background color of the window. This can be a color name (e.g., "red", "blue", "#RRGGBB") or any valid Tkinter color specification. If None, the default background color will be used. Defaults to None.
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
    """ Register an event handler for a specific event.

    This method allows you to register a handler function for a specific event related to the window. The supported events are "beforeclose" and "closed". The "beforeclose" event is triggered before the window is closed, and the handler can return False to prevent the window from closing. The "closed" event is triggered after the window has been closed. If an unsupported event name is provided, a ValueError will be raised.

    Args:
      event_name (str): The name of the event to register the handler for.
      handler (Callable[[Window], Any]): The handler function to be called when the event is triggered.
    """
    if not callable(handler):
      raise TypeError("handler must be callable")
    if event_name in self._events:
      self._events[event_name].append(handler)
    else:
      raise ValueError(f"Unsupported event name: {event_name} (use window.bind instead)")

  def is_dark_mode(self) -> bool:
    """ Check if the window is currently in dark mode.

    This method checks if the window is currently using a dark appearance mode. It is only supported on macOS, where it checks the "-isdark" attribute of the window. If the platform is not macOS, a NotImplementedError will be raised.
    """
    if _ismacos():
      return bool(self.window.attributes("-isdark"))
    raise NotImplementedError("is_dark_mode is only supported on macOS")

  def set_bounce(self, flag: bool) -> None:
    """ Enable or disable the bounce effect for the window.

    This method enables or disables the bounce effect for the window when it is minimized or when certain actions are performed. It is only supported on macOS, where it sets the "-bounce" attribute of the window. If the platform is not macOS, a NotImplementedError will be raised.
    """
    if _ismacos():
      self.window.attributes("-bounce", "1" if flag else "0")
    else:
      raise NotImplementedError("set_bounce is only supported on macOS")

  def get_bounce(self) -> bool:
    """ Get the current bounce effect status for the window.

    This method returns a boolean indicating whether the bounce effect is enabled for the window. It is only supported on macOS, where it checks the "-bounce" attribute of the window. If the platform is not macOS, a NotImplementedError will be raised.

    Returns:
      bool: True if the bounce effect is enabled, False otherwise.
    """
    if _ismacos():
      return bool(self.window.attributes("-bounce"))
    raise NotImplementedError("get_bounce is only supported on macOS")

  def set_modified_state(self, flag: bool) -> None:
    """ Set the modified state for the window.

    This method sets the modified state for the window. It is only supported on macOS, where it sets the "-modified" attribute of the window. If the platform is not macOS, a NotImplementedError will be raised.

    Args:
      flag (bool): True to set the modified state, False to clear it.
    """
    if _ismacos():
      self.window.attributes("-modified", "1" if flag else "0")
    else:
      raise NotImplementedError("set_modified_state is only supported on macOS")

  def get_modified_state(self) -> bool:
    """ Get the current modified state for the window.

    This method returns a boolean indicating whether the window has been modified. It is only supported on macOS, where it checks the "-modified" attribute of the window. If the platform is not macOS, a NotImplementedError will be raised.

    Returns:
      bool: True if the window has been modified, False otherwise.
    """
    if _ismacos():
      return bool(self.window.attributes("-modified"))
    raise NotImplementedError("get_modified_state is only supported on macOS")

  def set_window_alpha(self, alpha: float) -> None:
    """ Set the alpha (transparency) level for the window.

    This method sets the alpha level for the window, where 0.0 is fully transparent and 1.0 is fully opaque.

    Args:
      alpha (float): The alpha level to set, between 0.0 and 1.0.
    """
    alpha = _clamp(0.0, alpha, 1.0)
    self.window.attributes("-alpha", alpha)

  def get_window_alpha(self) -> float:
    """ Get the current alpha (transparency) level for the window.

    This method returns the current alpha level for the window, where 0.0 is fully transparent and 1.0 is fully opaque.

    Returns:
      float: The current alpha level of the window, between 0.0 and 1.0.
    """
    return float(self.window.attributes("-alpha"))

  def set_fullscreen(self, flag: bool) -> None:
    """ Enable or disable fullscreen mode for the window.

    This method enables or disables fullscreen mode for the window. When enabled, the window will occupy the entire screen and hide the title bar and borders.

    Args:
      flag (bool): True to enable fullscreen mode, False to disable it.
    """
    fullscreen = 1 if flag else 0
    self.window.attributes("-fullscreen", fullscreen)

  def is_fullscreen(self) -> bool:
    """ Check if the window is currently in fullscreen mode.

    This method returns a boolean indicating whether the window is currently in fullscreen mode. It checks the "-fullscreen" attribute of the window to determine the current fullscreen status.

    Returns:
      bool: True if the window is in fullscreen mode, False otherwise.
    """
    return bool(self.window.attributes("-fullscreen"))

  def set_topmost(self, flag: bool) -> None:
    """ Enable or disable always-on-top behavior for the window.

    This method enables or disables the always-on-top behavior for the window. When enabled, the window will be kept above all other windows on the screen.

    Args:
      flag (bool): True to enable always-on-top behavior, False to disable it.
    """
    topmost = 1 if flag else 0
    self.window.attributes("-topmost", topmost)

  def is_topmost(self) -> bool:
    """ Check if the window is currently set to always be on top.

    This method returns a boolean indicating whether the window is currently set to always be on top of other windows. It checks the "-topmost" attribute of the window to determine the current always-on-top status.

    Returns:
      bool: True if the window is set to always be on top, False otherwise.
    """
    return bool(self.window.attributes("-topmost"))

  def set_appearance_mode(self, mode: Literal["light", "dark"]) -> None:
    """ Set the appearance mode for the window.

    This method sets the appearance mode for the window. It is only supported on macOS, where it checks the "-appearance" attribute of the window.

    Args:
      mode (Literal["light", "dark"]): The appearance mode to set. "light" for light mode, "dark" for dark mode.
    """
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
    """ Set the background color for the window.

    This method sets the background color for the window.

    Args:
      color (str): The color to set as the background.
    """
    self.window.configure(background = color)

  def set_menu(self, menu: Menu) -> None:
    """ Set the menu for the window.

    This method sets the menu for the window.

    Args:
      menu (Menu): The menu to set.
    """
    menu.app = self.app
    self._menu = menu
    self.window.config(menu = menu.menu)

  def set_geometry(self, *, width: Optional[int] = None, height: Optional[int] = None, x: Optional[int] = None, y: Optional[int] = None) -> None:
    """ Set the geometry of the window.

    This method sets the geometry of the window, including its width, height, and position on the screen. If any of the parameters are None, the current value for that parameter will be used instead.
    """
    if width is None: width = self.window.winfo_width()
    if height is None: height = self.window.winfo_height()
    if x is None: x = self.window.winfo_x()
    if y is None: y = self.window.winfo_y()
    self.window.geometry(self.__geometry_str(width, height, x, y))

  def __geometry_str(self, width: int, height: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
    """ Convert geometry parameters to a string.

    Args:
      width (int): The width of the window.
      height (int): The height of the window.
      x (Optional[int]): The x-coordinate of the window's position.
      y (Optional[int]): The y-coordinate of the window's position.

    Returns:
      str: The geometry string.
    """
    if x is not None and y is not None:
      x_str = ("-" if x < 0 else "+") + str(abs(x))
      y_str = ("-" if y < 0 else "+") + str(abs(y))
      return f"{width}x{height}{x_str}{y_str}"
    return f"{width}x{height}"

  def focus(self) -> None:
    """ Set the focus to the window. """
    self.window.focus()

  def set_title(self, title: str) -> None:
    """ Set the title of the window.

    Args:
      title (str): The title to set for the window.
    """
    self.window.title(title)

  def close(self) -> bool:
    """ Close the window.

    This method attempts to close the window. It first triggers the "beforeclose" event handlers, allowing them to prevent the window from closing by returning False. If none of the handlers prevent the closure, the window is removed from the application's list of windows and destroyed. After the window is closed, the "closed" event handlers are triggered. The method returns True if the window was successfully closed, or False if the closure was prevented by a "beforeclose" event handler.

    Returns:
      bool: True if the window was closed, False if the closure was prevented.
    """
    for event in self._events["beforeclose"]:
      flag = event(self)
      if flag is not None and not flag:
        return False
    self.app._windows.remove(self)
    self.window.destroy()
    for event in self._events["closed"]:
      event(self)
    return True
