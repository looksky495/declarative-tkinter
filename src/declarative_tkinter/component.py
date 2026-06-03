import tkinter
import tkinter.font
import tkinter.ttk
import tkinter.scrolledtext
from abc import abstractmethod
from typing import Optional, Generic, TypeVar, Literal, Callable, Any, Self, cast, TypeAlias
import PIL.Image
import PIL.ImageTk
import random, string
import os

# Figureで管理するものと_figure_nameで管理するもの両方あって、なんかちょっと効率的じゃない気がする
# 将来的に_figure_nameを使った辞書管理に変更したらいいかも

_BlankImage: tkinter._Image | None = None
StrOrBytesPath: TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]

def create_nsimage_from_path(root: tkinter.Misc, path: StrOrBytesPath, width: Optional[int] = None, height: Optional[int] = None) -> str:
  """ Get a Tkinter image name from a file path.

  Get a Tkinter image name that can be used in the "image" option of widgets. The image is created as a "nsimage" type, which allows it to be displayed in widgets without being garbage collected. The image is created with the specified width and height if provided, otherwise it will use the original size of the image file.

  Args:
    root: The root widget to use for creating the image.
    path: The file path of the image.
    width: The width of the image.
    height: The height of the image.

  Returns:
    str: The name of the created image that can be used in the "image" option of widgets.
  """
  name = random_string(12)
  root.tk.call(
    "image", "create", "nsimage", name,
    "-source", str(path),
    "-as", "file",
    *(["-width", width] if width is not None else []),
    *(["-height", height] if height is not None else []),
  )
  return name


def _get_blank_image() -> tkinter._Image:
  """ Get a blank image that can be used to make a Label with only text (no image) keep its size.

  This is a workaround for the fact that a Label with no image and only text will shrink to fit the text, which can cause layout issues when the text changes. By using a blank image, we can ensure that the Label maintains a consistent size regardless of the text content.

  Returns:
    tkinter._Image: A blank image that can be used in a Label widget.
  """
  global _BlankImage
  if _BlankImage is None:
    _BlankImage = PIL.ImageTk.PhotoImage(PIL.Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
  return _BlankImage

def random_string(length: int) -> str:
  """ Generate a random string of the specified length.

  The first character is guaranteed to be a letter, and the rest of the characters can be letters or digits. This is useful for generating unique names for Tkinter styles or images.

  Args:
    length: The length of the random string to generate. Must be at least 1.

  Returns:
    str: A random string of the specified length.
  """
  if length < 1:
    raise ValueError("length must be at least 1.")

  return random.choice(string.ascii_letters) + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length - 1))


class UIColor:
  """ A class representing a color in RGB format.

  The color is defined by three float values (r, g, b) representing the red, green, and blue components of the color, respectively. Each component can be in the range [0, max], where max is a float value that defaults to 255. The string representation of the color is in the format "#RRGGBB", where RR, GG, and BB are the hexadecimal values of the red, green, and blue components scaled to the range [0, 255].
  """

  def __init__(self, r: float, g: float, b: float, max: float = 255) -> None:
    """ Initialize a UIColor instance.

    Args:
      r: The red component of the color, as a float in the range [0, max].
      g: The green component of the color, as a float in the range [0, max].
      b: The blue component of the color, as a float in the range [0, max].
      max: The maximum value for each color component, as a float. Defaults to 255.
    """
    self.__r = r
    self.__g = g
    self.__b = b
    self.__max = max

  def __str__(self) -> str:
    """ Return the string representation of the color in the format "#RRGGBB".

    Each color component is scaled from the range [0, max] to the range [0, 255] and converted to a two-digit hexadecimal string. The resulting string is in the format "#RRGGBB", where RR, GG, and BB are the hexadecimal values of the red, green, and blue components, respectively.

    Returns:
      str: The string representation of the color in the format "#RRGGBB".
    """
    hex_r = f"{int(self.__r / self.__max * 255):0>2x}"
    hex_g = f"{int(self.__g / self.__max * 255):0>2x}"
    hex_b = f"{int(self.__b / self.__max * 255):0>2x}"
    return f"#{hex_r}{hex_g}{hex_b}"

_UIColor = str | UIColor

def _decide_side(uiitem: UIItem | None):
  """ Decide the side to place the UI item based on its type.

  Args:
    uiitem: The UI item for which to decide the side.

  Returns:
    The side to place the UI item.
  """
  if isinstance(uiitem, HStack):
    return tkinter.LEFT
  else:
    return tkinter.TOP


class UIItem():
  """ The base class for all UI items.

  This class defines the common properties and methods for all UI items, such as padding, border, colors, event callbacks, and layout management. Each UI item can have a parent UI item and can contain child UI items. The layout method is responsible for creating the corresponding Tkinter widget and placing it in the parent widget according to the specified properties.
  """

  def __init__(self) -> None:
    """ Initialize a UIItem instance.

    This constructor initializes the properties of the UI item, such as the widget, parent UI item, contents, padding, border, colors, event callbacks, font, split weight, justification, and anchor. The widget is initially set to None and will be created in the layout method. The parent UI item is also set to None and will be assigned when the widget is placed in the parent widget. The contents are initialized as an empty tuple and can be populated by subclasses that contain child UI items.
    """
    self.widget: Optional[tkinter.Widget] = None
    self.parent_uiitem: Optional[UIItem] = None
    self.contents: tuple[UIItem, ...] = ()
    self._id: Optional[int] = None
    self._name: Optional[str] = None
    self._padding_pady: int = 0
    self._padding_padx: int = 0
    self._padding_4: Optional[tuple[int, int, int, int]] = None
    self._border_style: Literal["flat", "raised", "sunken", "groove", "ridge"] = "flat"
    self._border_width: int = 0
    self._highlight_back_color: Optional[str] = None
    self._highlight_focus_color: Optional[str] = None
    self._highlight_width: Optional[int] = 0
    self._foreground_color: Optional[str] = None
    self._background_color: Optional[str] = None
    self._fill_direction: Optional[str] = None
    self._fill_expand: bool = False
    self._cursor_type: Optional[str] = None
    self._frame_width: Optional[int] = None
    self._frame_height: Optional[int] = None
    self._callback_clicked: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any] = lambda *_: None
    self._callback_mouse_enter: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any] = lambda *_: None
    self._callback_mouse_leave: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any] = lambda *_: None
    self._font: Optional[tkinter.font._FontDescription] = None
    self._split_weight: Optional[int] = None
    self._justify: Optional[Literal["left", "center", "right"]] = None
    self._anchor: Optional[Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "center"]] = None
    # for grid
    self._column_span: int = 1
    self._row_span: int = 1
    self._is_hidden: bool = False

  def name(self, name: str) -> Self:
    """ Set the name of the UI item.

    This method assigns a name to the UI item, which can be used to retrieve the item later using the getUIByName method. The name is stored in the _name property of the UI item. The method returns self to allow for method chaining.

    Args:
      name: The name to assign to the UI item.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._name = name
    return self

  def getUIByName(self, name: str) -> Optional[UIItem]:
    """ Get a UI item by its name.

    This method searches for a UI item with the specified name in the current UI item and its contents. If a UI item with the matching name is found, it is returned. If no matching UI item is found, None is returned. The search is performed recursively through the contents of the UI item, allowing for nested UI items to be found by name.

    Args:
      name: The name of the UI item to search for.

    Returns:
      Optional[UIItem]: The UI item with the specified name, or None if no such item is found.
    """
    if self._name == name:
      return self
    for item in self.contents:
      searched = item.getUIByName(name)
      if searched is not None:
        return searched

  def takeout(self, *, out: WidgetVar) -> Self:
    """ Take out this UI item (UIItem) and assign it to the provided WidgetVar.

    Note:
      WidgetVar stores a reference to a UIItem instance. If you need the underlying
      Tkinter widget, access it via ``out.value.widget`` after layout.

    Args:
      out: A WidgetVar instance to which this UI item will be assigned.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    out.value = self
    return self

  @abstractmethod
  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Widget: ...

  def _make_kwargs(self, args: list[str]) -> dict:
    """ Make a dictionary of keyword arguments for widget configuration based on the specified properties of the UI item.

    Args:
      args: A list of property names to include in the keyword arguments. The possible property names are "padxy", "pad4", "fg", "bg", "bd", "highlight", "fill", "frame", "width", "height", "cursor", "font", "anchor", and "justify". The method checks the corresponding properties of the UI item and includes them in the resulting dictionary if they are specified.

    Returns:
      dict: A dictionary of keyword arguments for widget configuration based on the specified properties of the UI item.
    """
    kwargs = {}
    if "padxy" in args:
      kwargs["pady"] = self._padding_pady
      kwargs["padx"] = self._padding_padx
    if "pad4" in args and self._padding_4 is not None:
      kwargs["padding"] = self._padding_4
    if "fg" in args and self._foreground_color is not None:
      kwargs["foreground"] = self._foreground_color
    if "bg" in args and self._background_color is not None:
      kwargs["background"] = self._background_color
    if "bd" in args:
      kwargs["bd"] = self._border_width
      kwargs["relief"] = self._border_style
    if "highlight" in args:
      kwargs["highlightbackground"] = self._highlight_back_color
      kwargs["highlightcolor"] = self._highlight_focus_color
      kwargs["highlightthickness"] = self._highlight_width
    if "fill" in args and self._fill_direction is not None:
      kwargs["fill"] = self._fill_direction
      kwargs["expand"] = self._fill_expand
    if ("frame" in args or "width" in args) and self._frame_width is not None:
      kwargs["width"] = self._frame_width
    if ("frame" in args or "height" in args) and self._frame_height is not None:
      kwargs["height"] = self._frame_height
    if "cursor" in args and self._cursor_type is not None:
      kwargs["cursor"] = self._cursor_type
    if "font" in args and self._font is not None:
      kwargs["font"] = self._font
    if "anchor" in args and self._anchor is not None:
      kwargs["anchor"] = self._anchor
    if "justify" in args and self._justify is not None:
      kwargs["justify"] = self._justify
    return kwargs

  def _inherit_background(self, parent_uiitem: UIItem | None) -> None:
    """ Inherit the background color from the parent UI item if the background color of this UI item is not specified.

    This method checks if the _background_color property of this UI item is None. If it is None, it assigns the background color of the parent UI item to this UI item. This allows child UI items to inherit the background color of their parent UI item if they do not have a specific background color set.

    Args:
      parent_uiitem: The parent UI item from which to inherit the background color if this UI item does not have a specific background color set.
    """
    if self._background_color is None:
      self._background_color = parent_uiitem._background_color if parent_uiitem else None

  def _place_widget(self, widget: tkinter.Widget, parent_uiitem: UIItem | None, kwargs: list[str]) -> None:
    """ Place the widget in the parent widget according to the specified properties of the UI item.

    This method binds the click, mouse enter, and mouse leave events to the widget if the UI item is not hidden. It then places the widget in the parent widget using either pack or grid layout management, depending on the type of the parent UI item. If the parent UI item is a Grid, the placement is handled by the GridRow class, so this method does not place the widget directly. Finally, it sets the widget ID and marks the UI item as not hidden.

    Args:
      widget: The Tkinter widget to place in the parent widget.
      parent_uiitem: The parent UI item in which to place the widget.
      kwargs: A list of property names to include in the keyword arguments for widget configuration. This is passed to the _make_kwargs method to generate the appropriate keyword arguments for widget configuration.
    """
    if not self._is_hidden:
      widget.bind("<Button-1>", lambda event: self._callback_clicked(self, event))
      widget.bind("<Enter>", lambda event: self._callback_mouse_enter(self, event))
      widget.bind("<Leave>", lambda event: self._callback_mouse_leave(self, event))

    self.parent_uiitem = parent_uiitem

    if not isinstance(parent_uiitem, Grid):
      # pack
      widget.pack(side = _decide_side(parent_uiitem), **self._make_kwargs(kwargs))
    else:
      # gridはここで配置しない（GridRowに処理を任せる）
      pass
    self._set_widget_id()
    self._is_hidden = False

  def _set_widget_id(self) -> None:
    """ Set the widget ID for this UI item.

    This method retrieves the widget ID using the winfo_id method of the widget and assigns it to the _id property of this UI item. The widget ID is a unique identifier for the widget that can be used for various purposes, such as event handling or debugging. If the widget is not set, a ValueError is raised.
    """
    if self.widget is not None:
      self._id = self.widget.winfo_id()
    else:
      raise ValueError("Widget is not set.")

  def hide(self) -> None:
    """ Hide the widget of this UI item.

    This method hides the widget of this UI item by calling the appropriate method to remove it from the layout. If the parent UI item is a Grid, the grid_remove method is called to hide the widget while preserving its grid configuration. For other types of parent UI items, the pack_forget method is called to hide the widget. Finally, the _is_hidden property is set to True to indicate that the UI item is now hidden.
    """
    if self.widget is not None and not self._is_hidden:
      if isinstance(self.parent_uiitem, Grid):
        self.widget.grid_remove()
      else:
        self.widget.pack_forget()
    self._is_hidden = True


  def padding(self, all: Optional[int] = None, /, *, vertical: Optional[int] = None, horizontal: Optional[int] = None) -> Self:
    """ Set the padding for this UI item.

    This method sets the padding for the UI item. If all is specified, it sets both vertical and horizontal padding to that value. If vertical or horizontal is specified, it sets only those values.

    Args:
      all: The padding to apply to all sides of the UI item. If specified, it overrides the vertical and horizontal padding values.
      vertical: The vertical padding to apply to the UI item. This is ignored if the all parameter is specified.
      horizontal: The horizontal padding to apply to the UI item. This is ignored if the all parameter is specified.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    if all is not None:
      self._padding_pady = all
      self._padding_padx = all
    if vertical is not None:
      self._padding_pady = vertical
    if horizontal is not None:
      self._padding_padx = horizontal
    return self

  def borderWidth(self, width: int, /) -> Self:
    """ Set the border width for this UI item.

    Args:
      width: The width of the border to apply to the UI item.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    if width is not None:
      self._border_width = width
    return self

  def focusBorder(self, *, backColor: Optional[_UIColor] = None, focusColor: Optional[_UIColor] = None, width: Optional[int] = 1) -> Self:
    """ Set the focus border for this UI item.

    Args:
      backColor: The background color of the border when not focused.
      focusColor: The color of the border when focused.
      width: The width of the border.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    if backColor is not None:
      self._highlight_back_color = str(backColor)
    if focusColor is not None:
      self._highlight_focus_color = str(focusColor)
    if width is not None:
      self._highlight_width = width
    return self

  def foregroundColor(self, color: _UIColor) -> Self:
    """ Set the foreground color for this UI item.

    Args:
      color: The color to apply to the foreground of the UI item.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._foreground_color = str(color)
    return self

  def backgroundColor(self, color: Optional[_UIColor] = None) -> Self:
    """ Set the background color for this UI item.

    Args:
      color: The color to apply to the background of the UI item.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    if color is not None:
      self._background_color = str(color)
    else:
      self._background_color = None
    if self.widget is not None:
      try:
        if self._background_color is None: self._inherit_background(self.parent_uiitem)
        self.widget.configure(bg = self._background_color) # type: ignore
      except tkinter.TclError as e:
        print(str(e))
    return self

  def fill(self, direction: Literal["x", "y", "both"], /, *, expand: bool = False) -> Self:
    """ Set the fill direction and expand option for this UI item.

    Args:
      direction: The direction in which the UI item should fill its available space.
      expand: Whether the UI item should expand to fill its available space.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._fill_direction = direction
    self._fill_expand = expand
    return self

  def pointer(self, cursor_type: str) -> Self:
    """ Set the cursor type for this UI item.

    Args:
      cursor_type: The type of cursor to display when the mouse pointer is over the UI item. This should be a valid cursor type recognized by Tkinter, such as "arrow", "hand2", "cross", etc.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._cursor_type = cursor_type
    return self

  def frame(self, *, width: Optional[int] = None, height: Optional[int] = None) -> Self:
    """ Set the frame size for this UI item.

    Args:
      width: The width of the frame to apply to the UI item. If not specified, the width will not be set and the UI item will use its default width.
      height: The height of the frame to apply to the UI item. If not specified, the height will not be set and the UI item will use its default height.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    if width is not None:
      self._frame_width = width
    if height is not None:
      self._frame_height = height
    return self

  def font(self, fontDescription: tkinter.font._FontDescription, /) -> Self:
    """ Set the font for this UI item.

    Args:
      fontDescription: The font description to apply to the UI item. This should be a valid font description recognized by Tkinter, such as a tuple of (family, size, style) or a string representing the font.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._font = fontDescription
    return self

  def alignment(self, anchor: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "center", "leading", "trailing"]) -> Self:
    """ Set the alignment for this UI item.

    Args:
      anchor: The anchor point for the UI item. This should be a valid anchor type recognized by Tkinter, such as "n", "ne", "e", "se", "s", "sw", "w", "nw", "center", "leading", "trailing".

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    if anchor == "leading":
      anchor = "w"
    if anchor == "trailing":
      anchor = "e"
    self._anchor = anchor
    return self

  def justify(self, justify: Literal["left", "center", "right"]) -> Self:
    """ Set the justification for this UI item.

    Args:
      justify: The justification for the UI item. This should be a valid justification type recognized by Tkinter, such as "left", "center", "right".

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._justify = justify
    return self

  def onClicked(self, callback: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any]) -> Self:
    """ Set the callback function to be called when this UI item is clicked.

    Args:
      callback: A callable function that takes two arguments: the UI item instance and the Tkinter event object. This function will be called when the UI item is clicked.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._callback_clicked = callback
    return self

  def onMouseEnter(self, callback: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any]) -> Self:
    """ Set the callback function to be called when the mouse pointer enters this UI item.

    Args:
      callback: A callable function that takes two arguments: the UI item instance and the Tkinter event object. This function will be called when the mouse pointer enters the UI item.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._callback_mouse_enter = callback
    return self

  def onMouseLeave(self, callback: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any]) -> Self:
    """ Set the callback function to be called when the mouse pointer leaves this UI item.

    Args:
      callback: A callable function that takes two arguments: the UI item instance and the Tkinter event object. This function will be called when the mouse pointer leaves the UI item.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._callback_mouse_leave = callback
    return self

  def splitWeight(self, weight: int) -> Self:
    """ Set the split weight for this UI item when it is used in a split view (e.g., VSplitView).

    Args:
      weight: The split weight to assign to this UI item. This should be a positive integer that determines how much space this UI item will take relative to other items in the same split view. A higher weight means the item will take more space.
    """
    self._split_weight = weight
    return self

  def rowSpan(self, span: int) -> Self:
    """ Set the row span for this UI item when it is used in a grid layout.

    Args:
      span: The number of rows this UI item should span. This should be a positive integer.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    if span < 1 or not isinstance(span, int):
      raise ValueError("span must be positive integer.")
    self._row_span = span
    return self

  def columnSpan(self, span: int) -> Self:
    """ Set the column span for this UI item when it is used in a grid layout.

    Args:
      span: The number of columns this UI item should span. This should be a positive integer.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    if span < 1 or not isinstance(span, int):
      raise ValueError("span must be positive integer.")
    self._column_span = span
    return self

  def disable(self, flag: bool = True):
    """ Disable or enable the widget of this UI item.

    Args:
      flag: If True, the widget will be disabled. If False, the widget will be enabled. Defaults to True.
    """
    self._is_disabled = not not flag
    if self.widget is not None:
      self.widget["state"] = tkinter.DISABLED if self._is_disabled else tkinter.NORMAL


class Rectangle (UIItem):
  """ A simple rectangular UI item that can be used as a spacer or background element.

  This class creates a Frame widget with the specified width and height, and can be configured with background color, border, padding, and other properties inherited from the UIItem base class. The Rectangle can be used to create empty space between other UI items or to provide a colored background for other UI items.
  """

  def __init__(self, *, width: int, height: int) -> None:
    """ Initialize a Rectangle instance.

    Args:
      width: The width of the rectangle in pixels.
      height: The height of the rectangle in pixels.
    """

    super().__init__()
    self.width = width
    self.height = height

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Frame:
    """ Layout the rectangle within its parent widget.

    Args:
      parent_widget: The parent widget to which the rectangle will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the rectangle does not have its own background color specified.

    Returns:
      The Tkinter Frame widget representing the rectangle.
    """
    self._inherit_background(parent_uiitem)

    self.widget = tkinter.Frame(
      parent_widget,
      width = self.width,
      height = self.height,
      **self._make_kwargs(["bg", "bd", "cursor", "highlight"])
    )
    self._place_widget(self.widget, parent_uiitem, ["padxy", "fill"])
    return self.widget

class VStack (UIItem):
  """ A vertical stack UI item that arranges its child UI items in a vertical layout.

  This class creates a Frame widget that contains its child UI items arranged vertically. The child UI items are added to the contents property of the VStack, and the layout method is responsible for creating the Frame widget and placing the child UI items within it. The VStack can be configured with background color, border, padding, and other properties inherited from the UIItem base class. The add method allows for dynamically adding child UI items to the VStack after it has been created.
  """

  def __init__(self, *contents: UIItem) -> None:
    """ Initialize a VStack instance.

    Args:
      contents: The UI items to include in the vertical stack.
    """
    super().__init__()
    self.contents = contents

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Frame:
    """ Layout the vertical stack within its parent widget.

    Args:
      parent_widget: The parent widget to which the vertical stack will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the vertical stack does not have its own background color specified.

    Returns:
      The Tkinter Frame widget representing the vertical stack.
    """

    self._inherit_background(parent_uiitem)

    if self.widget is None:
      self.widget = tkinter.Frame(
        parent_widget,
        **self._make_kwargs(["bg", "bd", "frame", "cursor", "highlight"])
      )

      for item in self.contents:
        item.layout(self.widget, self)
      if self._frame_height is not None or self._frame_width is not None:
        self.widget.pack_propagate(False)
    elif self._is_hidden:
      self.widget: tkinter.Frame # type: ignore
      parent_uiitem = self.parent_uiitem
    else:
      return self.widget # 隠されてないから
    self._place_widget(self.widget, parent_uiitem, ["padxy", "fill"])
    return self.widget

  def add(self, item: UIItem) -> tkinter.Widget:
    """ Add a child UI item to the vertical stack.

    Args:
      item: The UI item to add to the vertical stack.

    Returns:
      The Tkinter widget corresponding to the added UI item.
    """
    if self.widget is None:
      raise ValueError("VStack widget is not yet created.")
    widget = item.layout(self.widget, self)
    self.contents += (item,)
    return widget

class HStack (VStack): ...

class VSplitView (UIItem):
  """ A vertical split view UI item that arranges its child UI items in a vertical layout with adjustable dividers.

  This class creates a PanedWindow widget that contains its child UI items arranged vertically with adjustable dividers (sashes) between them. The child UI items are added to the contents property of the VSplitView, and the layout method is responsible for creating the PanedWindow widget and placing the child UI items within it. The VSplitView can be configured with background color, border, padding, sash width, sash color, border color, and other properties inherited from the UIItem base class. The add method allows for dynamically adding child UI items to the VSplitView after it has been created.
  """

  def __init__(self, *contents: UIItem) -> None:
    """ Initialize a VSplitView instance.

    Args:
      contents: The UI items to include in the vertical split view.
    """
    super().__init__()
    self.contents = contents
    self._sash_width: int = 3
    self._sash_color: Optional[str] = None
    self._border_color: Optional[str] = None
    self._orient: Literal["horizontal", "vertical"] = tkinter.HORIZONTAL
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None

  def sashWidth(self, width: int) -> Self:
    """ Set the width of the sash (divider) between the child UI items in the split view.

    Args:
      width: The width of the sash in pixels.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._sash_width = width
    return self

  def sashColor(self, color: _UIColor) -> Self:
    """ Set the color of the sash (divider) between the child UI items in the split view.

    Args:
      color: The color of the sash.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._sash_color = str(color)
    return self

  def borderColor(self, color: _UIColor) -> Self:
    """ Set the color of the border around the split view.

    Args:
      color: The color of the border.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._border_color = str(color)
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.PanedWindow:
    """ Layout the vertical split view within its parent widget.

    Args:
      parent_widget: The parent widget to which the vertical split view will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the vertical split view does not have its own background color specified.

    Returns:
      The Tkinter PanedWindow widget representing the vertical split view.
    """
    self._inherit_background(parent_uiitem)

    if self.widget is None:
      self._style_id = random_string(12)
      self._style = tkinter.ttk.Style(parent_widget)
      self._style.configure(
        f"{self._style_id}.TPanedwindow",
        **self._make_kwargs(["bg"])
      )
      self._style.configure(
        f"{self._style_id}.Sash",
        background = self._sash_color,
        bordercolor = self._border_color,
        sashthickness = self._sash_width,
      )

      self.widget = tkinter.ttk.Panedwindow(
        parent_widget,
        orient = self._orient,
        **self._make_kwargs(["frame"])
      )
      for item in self.contents:
        item_widget = item.layout(self.widget, self)
        self.widget.add(
          item_widget,
          weight = item._split_weight if item._split_weight is not None else 0
        )
      if self._frame_height is not None or self._frame_width is not None:
        self.widget.pack_propagate(False)
    elif self._is_hidden:
      self.widget: tkinter.PanedWindow # type: ignore
      parent_uiitem = self.parent_uiitem
    else:
      return self.widget
    self._place_widget(self.widget, parent_uiitem, ["padxy", "fill"])
    return self.widget

class HSplitView (VSplitView):
  """ A horizontal split view UI item that arranges its child UI items in a horizontal layout with adjustable dividers.

  This class inherits from VSplitView and overrides the orientation to create a horizontal split view. The child UI items are arranged horizontally with adjustable dividers (sashes) between them. The layout method is inherited from VSplitView and is responsible for creating the PanedWindow widget and placing the child UI items within it. The HSplitView can be configured with background color, border, padding, sash width, sash color, border color, and other properties inherited from the UIItem base class. The add method allows for dynamically adding child UI items to the HSplitView after it has been created.
  """

  def __init__(self, *contents: UIItem) -> None:
    """ Initialize a HSplitView instance.

    Args:
      contents: The UI items to include in the horizontal split view.
    """
    super().__init__(*contents)
    self._orient = tkinter.HORIZONTAL


class GridRow:
  """ A row in a grid layout that contains multiple UI items arranged horizontally.

  This class is used as part of the Grid layout system to define a row of UI items. Each GridRow contains a tuple of UI items that are arranged horizontally within the row. The layout method is responsible for placing the UI items in the correct columns of the grid, taking into account any column spans and reserved columns from previous rows. The GridRow does not directly create a widget, but instead relies on the Grid class to manage the overall grid layout and placement of the rows.
  """

  def __init__(self, *contents: UIItem) -> None:
    """ Initialize a GridRow instance.

    Args:
      contents: The UI items to include in the grid row.
    """
    self.contents = contents
    self._column_index: int = 0
    # 予約済みの列番号
    self._reserved_columns: list[int] = []

  def layout(self, parent_widget: tkinter.Frame, parent_uiitem: Grid) -> None:
    """ Layout the grid row within its parent grid.

    Args:
      parent_widget: The parent widget (Frame) to which the grid row will be added.
      parent_uiitem: The parent Grid UI item that manages the overall grid layout. This is used to access the current row index and manage reserved columns for proper placement of the UI items in the grid.
    """
    if not isinstance(parent_uiitem, Grid):
      raise ValueError("parent_uiitem must be Grid.")

    # print("Reserved columns:", self._reserved_columns)
    self._column_index = 0
    for column in self.contents:
      while len(self._reserved_columns) and self._column_index <= self._reserved_columns[0] < self._column_index + column._column_span:
        self._column_index = self._reserved_columns.pop(0) + 1
      widget = column.layout(parent_widget, parent_uiitem)
      widget.grid(
        row = parent_uiitem._row_index,
        column = self._column_index,
        rowspan = column._row_span,
        columnspan = column._column_span,
      )
      # print("row:", parent_uiitem._row_index, "column:", self._column_index, "rowspan:", column._row_span, "columnspan:", column._column_span)
      for i in range(1, column._row_span):
        row = i + parent_uiitem._row_index
        parent_uiitem.rows[row]._reserved_columns.extend(range(self._column_index, self._column_index + column._column_span))
        # print("Column reserved at column", range(self._column_index, self._column_index + column._column_span), " row", row)
      self._column_index += column._column_span

class Grid (VStack):
  """ A grid layout UI item that arranges its child UI items in a grid with rows and columns.

  This class creates a Frame widget that contains its child UI items arranged in a grid layout. The child UI items are organized into rows using the GridRow class, and the layout method is responsible for creating the Frame widget and placing the child UI items within it according to their specified row and column spans. The Grid can be configured with background color, border, padding, and other properties inherited from the UIItem base class. The add method allows for dynamically adding child UI items to the Grid after it has been created.
  """

  def __init__(self, *contents: GridRow) -> None:
    """ Initialize a Grid instance.

    Args:
      contents: The GridRow instances that define the rows of the grid layout.
    """

    super().__init__()
    self.rows: tuple[GridRow, ...] = contents
    self._row_index: int = 0

  def getUIByName(self, name: str) -> Optional[UIItem]:
    """ Search for a UI item by name within the grid and its child UI items.

    Args:
      name: The name of the UI item to search for.

    Returns:
      Optional[UIItem]: The UI item with the specified name if found, otherwise None.
    """
    if self._name == name:
      return self
    for row in self.rows:
      for item in row.contents:
        searched = item.getUIByName(name)
        if searched is not None:
          return searched
    return None

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Frame:
    """ Layout the grid within its parent widget.

    Args:
      parent_widget: The parent widget to which the grid will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the grid does not have its own background color specified.

    Returns:
      The Tkinter Frame widget representing the grid.
    """
    # hideされるとうまくshowできない？
    if self.widget is None:
      self.widget = super().layout(parent_widget, parent_uiitem)

      self._row_index = 0
      for row in self.rows:
        row.layout(self.widget, self)
        self._row_index += 1
      return self.widget
    elif self._is_hidden:
      self.widget: tkinter.Frame # type: ignore
      parent_uiitem = self.parent_uiitem
      return super().layout(parent_widget, parent_uiitem)
    else:
      return self.widget # 隠されてないから

class TabView (UIItem):
  """ A tab view UI item that contains multiple tabs, each with its own content.

  This class creates a Notebook widget that contains multiple tabs, each associated with a UI item that represents the content of the tab. The child UI items for each tab are defined in the tabs property, which is a tuple of (tab name, UI item) pairs. The layout method is responsible for creating the Notebook widget and placing the child UI items within their respective tabs. The TabView can be configured with background color, border, padding, and other properties inherited from the UIItem base class. The getUIByName method allows for searching for a specific UI item by name within the TabView and its child UI items.
  """

  def __init__(self, *contents: tuple[str, UIItem]) -> None:
    """ Initialize a TabView instance.

    Args:
      contents: A variable number of tuples, each containing a tab name (str) and a UI item that represents the content of the tab.
    """
    super().__init__()
    self.tabs: tuple[tuple[str, UIItem], ...] = contents
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None
    self._border_color: Optional[str] = None
    self._tab_background_color: Optional[str] = None

  def getUIByName(self, name: str) -> Optional[UIItem]:
    """ Search for a UI item by name within the tab view and its child UI items.

    Args:
      name: The name of the UI item to search for.

    Returns:
      Optional[UIItem]: The UI item with the specified name if found, otherwise None.
    """
    if self._name == name:
      return self
    for item in self.tabs:
      searched = item[1].getUIByName(name)
      if searched is not None:
        return searched
    return None

  def borderColor(self, color: _UIColor) -> Self:
    """ Set the color of the border around the tab view.

    Args:
      color: The color of the border.
    """
    self._border_color = str(color)
    return self

  def tabBackgroundColor(self, color: _UIColor) -> Self:
    """ Set the background color of the tabs in the tab view.

    Args:
      color: The background color of the tabs.
    """
    self._tab_background_color = str(color)
    return self

  def paddingOutside(self, all: int | None = None, /, *, vertical: int | None = None, horizontal: int | None = None, top: int | None = None, leading: int | None = None, bottom: int | None = None, trailing: int | None = None) -> Self:
    """ Set the outside padding for the tab view.

    Args:
      all: The padding to apply to all sides.
      vertical: The vertical padding.
      horizontal: The horizontal padding.
      top: The top padding.
      leading: The leading padding.
      bottom: The bottom padding.
      trailing: The trailing padding.
    """
    if all is not None:
      top = all
      leading = all
      bottom = all
      trailing = all
    if vertical is not None:
      top = vertical
      bottom = vertical
    if horizontal is not None:
      leading = horizontal
      trailing = horizontal

    self._padding_4 = (trailing or 0, top or 0, leading or 0, bottom or 0)
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Notebook:
    """ Layout the tab view within its parent widget.

    Args:
      parent_widget: The parent widget to which the tab view will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the tab view does not have its own background color specified.

    Returns:
      The Tkinter Notebook widget representing the tab view.
    """
    self._inherit_background(parent_uiitem)

    if self.widget is None:
      self._style_id = random_string(12)
      self._style = tkinter.ttk.Style(parent_widget)

      kwargs = {}
      if self._border_color is not None:
        kwargs["bordercolor"] = self._border_color
      tab_kwargs = {}
      if self._tab_background_color is not None:
        tab_kwargs["background"] = self._tab_background_color

      self._style.configure(
        f"{self._style_id}.TNotebook",
        **self._make_kwargs(["bg", "pad4", "bordercolor"]),
      )
      self._style.configure(
        f"{self._style_id}.TNotebook.Tab",
        **tab_kwargs,
        **self._make_kwargs(["bordercolor"]),
      )

      self.widget = tkinter.ttk.Notebook(
        parent_widget,
        style = f"{self._style_id}.TNotebook",
        **self._make_kwargs(["frame", "cursor"])
      )

      for name, item in self.tabs:
        widget = item.layout(self.widget, self)
        self.widget.add(widget, text = name)
      if self._frame_height is not None or self._frame_width is not None:
        self.widget.pack_propagate(False)
    elif self._is_hidden:
      self.widget: tkinter.ttk.Notebook # type: ignore
      parent_uiitem = self.parent_uiitem
    else:
      return self.widget
    self._place_widget(self.widget, parent_uiitem, ["padxy", "fill"])
    return self.widget


class Separator (UIItem):
  """ A separator UI item that creates a horizontal or vertical line to visually separate other UI items.

  This class creates a ttk.Separator widget that can be oriented either horizontally or vertically. The orientation can be specified when creating the Separator instance, or it can be automatically determined based on the parent UI item (e.g., if the parent is an HStack, the separator will be vertical; if the parent is a VStack, the separator will be horizontal). The Separator can be configured with background color, border, padding, and other properties inherited from the UIItem base class. The layout method is responsible for creating the Separator widget and placing it within its parent widget.
  """

  def __init__(self, orientation: Optional[Literal["horizontal", "vertical"]] = None) -> None:
    """ Initialize a Separator instance.

    Args:
      orientation: The orientation of the separator, either "horizontal" or "vertical". If not specified, the orientation will be automatically determined based on the parent UI item (e.g., if the parent is an HStack, the separator will be vertical; if the parent is a VStack, the separator will be horizontal).
    """
    super().__init__()
    self._orientation: Optional[Literal["horizontal", "vertical"]] = orientation
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None
    self.fill("both")

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Separator:
    """ Layout the separator within its parent widget.

    Args:
      parent_widget: The parent widget to which the separator will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the separator does not have its own background color specified.

    Returns:
      The Tkinter ttk.Separator widget representing the separator.
    """
    # self._inherit_background(parent_uiitem) inheritしない

    self._style = tkinter.ttk.Style(parent_widget)
    self._style_id = random_string(12)
    self._style.configure(
      f"{self._style_id}.TSeparator",
      **self._make_kwargs(["bg"]),
    )

    if self._orientation is None:
      if isinstance(parent_uiitem, HStack):
        self._orientation = "vertical"
      else:
        self._orientation = "horizontal"

    self.widget = tkinter.ttk.Separator(
      parent_widget,
      orient = self._orientation,
      style = f"{self._style_id}.TSeparator",
      **self._make_kwargs(["cursor"]),
    )
    self._place_widget(self.widget, parent_uiitem, ["padxy", "fill"])
    return self.widget


class Text (UIItem):
  """ A text UI item that displays a string of text.

  This class creates a Label widget that displays the specified text. The Text can be configured with background color, foreground color, font, padding, and other properties inherited from the UIItem base class. The layout method is responsible for creating the Label widget and placing it within its parent widget. The setText method allows for updating the displayed text after the Text has been created.
  a.k.a. &lt;p /&gt; in HTML.
  """
  def __init__(self, text: str) -> None:
    """ Initialize a Text instance.

    Args:
      text: The string of text to display in the Text UI item.
    """
    super().__init__()
    self.text = text

  # def paddingOutside(self, all: int | None = None, /, *, vertical: int | None = None, horizontal: int | None = None, top: int | None = None, leading: int | None = None, bottom: int | None = None, trailing: int | None = None) -> Self:
  #   """ For ttk Widgets """
  #   if all is not None:
  #     top = all
  #     leading = all
  #     bottom = all
  #     trailing = all
  #   if vertical is not None:
  #     top = vertical
  #     bottom = vertical
  #   if horizontal is not None:
  #     leading = horizontal
  #     trailing = horizontal

  #   self._padding_4 = (trailing or 0, top or 0, leading or 0, bottom or 0)
  #   return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Label:
    """ Layout the text within its parent widget.

    Args:
      parent_widget: The parent widget to which the text will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the text does not have its own background color specified.

    Returns:
      The Tkinter Label widget representing the text.
    """
    self._inherit_background(parent_uiitem)

    self.widget = tkinter.Label(
      parent_widget,
      text = self.text,
      image = _get_blank_image(),
      compound = "center",
      **self._make_kwargs(["bg", "fg", "bd", "cursor", "highlight", "font", "frame", "justify", "anchor"])
    )
    # print(self._make_kwargs(["bg", "fg", "bd", "cursor", "highlight", "font", "frame", "justify"]))
    self._place_widget(self.widget, parent_uiitem, ["padxy"])
    return self.widget

  def setText(self, text: str) -> None:
    """ Set the text to be displayed in the Text UI item.

    Args:
      text: The new string of text to display in the Text UI item.
    """
    if isinstance(self.widget, tkinter.Label):
      self.widget.configure(text = text)
    self.text = text

class TextField (UIItem):
  """ A text field UI item that allows the user to input a single line of text.

  This class creates an Entry widget that allows the user to input a single line of text. The TextField can be configured with background color, foreground color, font, padding, and other properties inherited from the UIItem base class. The layout method is responsible for creating the Entry widget and placing it within its parent widget. The onChange method allows for setting a callback function that will be called whenever the text in the TextField changes, and the onSubmit method allows for setting a callback function that will be called when the user presses the Enter key while the TextField is focused.
  """

  def __init__(self, variable: tkinter.StringVar, /, *, placeholder: Optional[str] = None) -> None:
    """ Initialize a TextField instance.

    Args:
      variable: A tkinter.StringVar that will be used to store the text entered in the TextField. This variable will be updated automatically as the user types in the TextField.
      placeholder: An optional string that will be displayed in the TextField when it is empty, as a hint to the user about what to enter. This is similar to the placeholder attribute in HTML input elements.
    """
    super().__init__()
    self.variable = variable
    self.placeholder = placeholder
    self.is_secure = False
    self._style: Optional[tkinter.ttk.Style] = None
    self._placeholder_color: Optional[str] = None
    self._callback_change: Callable[[TextField, tkinter.StringVar], Any] = lambda *_: None
    self._callback_submit: Callable[[TextField, tkinter.StringVar], Any] = lambda *_: None

  def width(self, width: int) -> Self:
    """ Set the width of the TextField in characters.

    Args:
      width: The width of the TextField in characters. This will determine how many characters can be displayed in the TextField at once without scrolling. Note that the actual pixel width of the TextField will depend on the font and other styling properties.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._frame_width = width
    return self

  def placeholderColor(self, color: _UIColor) -> Self:
    """ Set the color of the placeholder text in the TextField.

    Args:
      color: The color to use for the placeholder text.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._placeholder_color = str(color)
    return self

  def onChange(self, callback: Callable[[TextField, tkinter.StringVar], Any]) -> Self:
    """ Set a callback function that will be called whenever the text in the TextField changes.

    Args:
      callback: A function that takes two arguments: the TextField instance and the tkinter.StringVar that contains the current text in the TextField. This function will be called whenever the text in the TextField changes, either due to user input or programmatically.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._callback_change = callback
    return self

  def onSubmit(self, callback: Callable[[TextField, tkinter.StringVar], Any]) -> Self:
    """ Set a callback function that will be called when the user presses the Enter key while the TextField is focused.

    Args:
      callback: A function that takes two arguments: the TextField instance and the tkinter.StringVar that contains the current text in the TextField. This function will be called when the user presses the Enter key while the TextField is focused.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._callback_submit = callback
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Entry:
    """ Layout the text field within its parent widget.

    Args:
      parent_widget: The parent widget to which the text field will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the text field does not have its own background color specified.

    Returns:
      The Tkinter Entry widget representing the text field.
    """
    self._inherit_background(parent_uiitem)

    self._style = tkinter.ttk.Style(parent_widget)
    self._style_id = f"{random_string(12)}.TEntry"
    self._style.configure(
      self._style_id,
      **self._make_kwargs(["bg", "fg", "bd", "pad4"])
    )

    kwargs = {}
    if self._placeholder_color is not None:
      kwargs["placeholderforeground"] = self._placeholder_color

    self.widget = tkinter.ttk.Entry(
      parent_widget,
      textvariable = self.variable,
      placeholder = self.placeholder if self.placeholder is not None else "", # type: ignore
      show = "*" if self.is_secure else "",
      style = self._style_id,
      **kwargs,
      **self._make_kwargs(["cursor", "width", "font", "justify"])
    )
    self._place_widget(self.widget, parent_uiitem, ["fill"])
    self._set_widget_id()

    self.variable.trace_add("write", lambda *_: self._callback_change(self, self.variable))
    self.widget.bind("<KeyPress-Return>", lambda *_: self._callback_submit(self, self.variable))
    self.widget.bind("<<Modified>>", lambda *_: self._callback_change(self, self.variable))
    return self.widget

class SecureField (TextField):
  """ A secure text field UI item that allows the user to input a single line of text, but masks the input for privacy.

  This class inherits from TextField and overrides the layout method to create an Entry widget with the show option set to "*" (or any other character) to mask the input. The SecureField can be configured with background color, foreground color, font, padding, and other properties inherited from the UIItem base class. The onChange and onSubmit methods can be used to set callback functions for when the text changes or when the user presses Enter, just like in the TextField class.
  """

  def __init__(self, variable: tkinter.StringVar, /, *, placeholder: Optional[str] = None) -> None:
    """ Initialize a SecureField instance.

    Args:
      variable: A tkinter.StringVar that will be used to store the text entered in the SecureField. This variable will be updated automatically as the user types in the SecureField.
      placeholder: An optional string that will be displayed in the SecureField when it is empty, as a hint to the user about what to enter. This is similar to the placeholder attribute in HTML input elements.
    """
    super().__init__(variable, placeholder = placeholder)
    self.is_secure = True

_TextWidgets = tkinter.Text | tkinter.scrolledtext.ScrolledText

class TextEditor (UIItem):
  """ A text editor UI item that allows the user to input and edit multiple lines of text.

  This class creates a Text widget (or a ScrolledText widget if scrollable is True) that allows the user to input and edit multiple lines of text. The TextEditor can be configured with background color, foreground color, font, padding, and other properties inherited from the UIItem base class. The onChange method allows for setting a callback function that will be called whenever the text in the TextEditor changes. The wrap option can be set to control how the text wraps within the TextEditor, and the scrollable option can be set to determine whether a scrollbar is included for the TextEditor when the content exceeds the visible area. The layout method is responsible for creating the Text or ScrolledText widget and placing it within its parent widget. The __text_modified method is used as a callback for the <<Modified>> event of the Text widget to detect when the text has been modified and call the onChange callback accordingly.
  """

  def __init__(self, /, *, wrap: Literal["none", "char", "word"] = "word", scrollable: bool = True) -> None:
    """ Initialize a TextEditor instance.

    Args:
      wrap: A string that specifies how the text should wrap within the TextEditor. It can be "none" for no wrapping, "char" for wrapping at any character, or "word" for wrapping at word boundaries. The default is "word".
      scrollable: A boolean that determines whether the TextEditor should include a scrollbar when the content exceeds the visible area. If True, a ScrolledText widget will be used, which includes a vertical scrollbar. If False, a regular Text widget will be used without a scrollbar. The default is True.
    """
    super().__init__()
    self._wrap: Literal["none", "char", "word"] = wrap
    self._scrollable = scrollable
    self._callback_change: Callable[[tkinter.Event[_TextWidgets], TextEditor], Any] = lambda *_: None

  def width(self, width: int) -> Self:
    """ Set the width of the TextEditor in characters.

    Args:
      width: The width of the TextEditor in characters. This will determine how many characters can be displayed in the TextEditor at once without scrolling horizontally. Note that the actual pixel width of the TextEditor will depend on the font and other styling properties.
    """
    self._frame_width = width
    return self

  def height(self, height: int) -> Self:
    """ Set the height of the TextEditor in characters.

    Args:
      height: The height of the TextEditor in characters. This will determine how many lines can be displayed in the TextEditor at once without scrolling vertically. Note that the actual pixel height of the TextEditor will depend on the font and other styling properties.
    """
    self._frame_height = height
    return self

  def onChange(self, callback: Callable[[tkinter.Event[_TextWidgets], TextEditor], Any]) -> Self:
    """ Set a callback function that will be called whenever the text in the TextEditor changes.

    Args:
      callback: A function that takes two arguments: a tkinter.Event object that contains information about the event that triggered the change (such as the widget that was modified), and the TextEditor instance itself. This function will be called whenever the text in the TextEditor changes, either due to user input or programmatically.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._callback_change = callback
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Text:
    """ Layout the text editor within its parent widget.

    Args:
      parent_widget: The parent widget to which the text editor will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the text editor does not have its own background color specified.
    """
    self._inherit_background(parent_uiitem)

    self.widget = (tkinter.scrolledtext.ScrolledText if self._scrollable else tkinter.Text)(
      parent_widget,
      wrap = self._wrap,
      **self._make_kwargs(["cursor", "frame", "font", "justify", "highlight", "bd", "bg"])
    )
    self._place_widget(self.widget, parent_uiitem, ["fill"])
    self._set_widget_id()

    self.widget.bind("<<Modified>>",  self.__text_modified)
    return self.widget

  def __text_modified(self, event: tkinter.Event[tkinter.Text]):
    """ Internal callback function that is called when the text in the TextEditor is modified. This function checks if the text has been modified, and if so, it calls the onChange callback function with the event and the TextEditor instance as arguments. After calling the onChange callback, it resets the modified flag of the Text widget to False.

    Args:
      event: A tkinter.Event object that contains information about the event that triggered the modification, such as the widget that was modified.
    """
    self.widget: tkinter.Text # type: ignore
    if self.widget.edit_modified():
      self._callback_change(event, self)
    self.widget.edit_modified(False)


StepperT = TypeVar("StepperT", bound = tkinter.Variable)

class Stepper (UIItem, Generic[StepperT]):
  """ A stepper UI item that allows the user to select a value from a range by incrementing or decrementing it.

  This class creates a Spinbox widget that allows the user to select a value from a specified range by incrementing or decrementing it using the up and down arrows. The Stepper can be configured with a range of values (using the within method), a step size (using the step method), a placeholder text (using the placeholder method), and whether the values should wrap around when reaching the minimum or maximum (using the wrap method). The onChange method allows for setting a callback function that will be called whenever the value in the Stepper changes, and the onSubmit method allows for setting a callback function that will be called when the user presses the Enter key while the Stepper is focused. The layout method is responsible for creating the Spinbox widget and placing it within its parent widget.
  """

  def __init__(self, variable: StepperT, /, *, within: tuple[float, float] | None = None, step: float | None = None, placeholder: str | None = None, wrap: bool | None = None) -> None:
    """ Initialize a Stepper instance.

    Args:
      variable: A tkinter.Variable (such as IntVar or DoubleVar) that will be used to store the current value of the Stepper. This variable will be updated automatically as the user increments or decrements the value in the Stepper.
      within: An optional tuple specifying the minimum and maximum values for the Stepper. The user will only be able to select values within this range.
      step: An optional float specifying the step size for incrementing or decrementing the value in the Stepper. For example, if step is 0.5, the user will be able to select values that are 0.5 apart (e.g., 0, 0.5, 1.0, 1.5, etc.).
      placeholder: An optional string that will be displayed in the Stepper when it is empty, as a hint to the user about what to enter. This is similar to the placeholder attribute in HTML input elements.
      wrap: An optional boolean that determines whether the values in the Stepper should wrap around when reaching the minimum or maximum. If True, when the user increments the value past the maximum, it will wrap around to the minimum, and when the user decrements the value past the minimum, it will wrap around to the maximum. If False, the user will not be able to increment or decrement past the minimum or maximum values. The default is False.
    """
    super().__init__()
    self.variable = variable
    self._within = within
    self._step = step
    self._placeholder = placeholder
    self._wrap = wrap
    self._format: Optional[str] = None
    self._placeholder_color: Optional[str] = None
    self._style: Optional[tkinter.ttk.Style] = None
    self._stepper_width: Optional[int] = None
    self._callback_change: Callable[[Stepper[StepperT], StepperT], Any] = lambda *_: None
    self._callback_submit: Callable[[Stepper[StepperT], StepperT], Any] = lambda *_: None

  def onChange(self, callback: Callable[[Stepper[StepperT], StepperT], Any]) -> Self:
    """ Set a callback function that will be called whenever the value in the Stepper changes.

    Args:
      callback: A function that takes two arguments: the Stepper instance and the tkinter.Variable that contains the current value of the Stepper. This function will be called whenever the value in the Stepper changes, either due to user input or programmatically.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._callback_change = callback
    return self

  def onSubmit(self, callback: Callable[[Stepper[StepperT], StepperT], Any]) -> Self:
    """ Set a callback function that will be called when the user presses the Enter key while the Stepper is focused.

    Args:
      callback: A function that takes two arguments: the Stepper instance and the tkinter.Variable that contains the current value of the Stepper. This function will be called when the user presses the Enter key while the Stepper is focused.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._callback_submit = callback
    return self

  def placeholderColor(self, color: _UIColor) -> Self:
    """ Set the color of the placeholder text in the Stepper.

    Args:
      color: The color to use for the placeholder text.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._placeholder_color = str(color)
    return self

  def format(self, fmt: str) -> Self:
    """ Set the format string for the Stepper.

    Args:
      fmt: The format string to use for the Stepper.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._format = fmt
    return self

  def width(self, width: int) -> Self:
    """ Set the width of the Stepper in characters.

    Args:
      width: The width of the Stepper in characters. This will determine how many characters can be displayed in the Stepper at once without scrolling. Note that the actual pixel width of the Stepper will depend on the font and other styling properties.

    Returns:
      Self: The UI item instance itself, to allow for method chaining.
    """
    self._stepper_width = width
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Spinbox:
    """ Layout the stepper within its parent widget.

    Args:
      parent_widget: The parent widget to which the stepper will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the stepper does not have its own background color specified.

    Returns:
      tkinter.ttk.Spinbox: The created Spinbox widget.
    """
    self._inherit_background(parent_uiitem)

    self._style = tkinter.ttk.Style(parent_widget)
    self._style_id = f"{random_string(12)}.TSpinbox"
    self._style.configure(
      self._style_id,
      **self._make_kwargs(["bg", "fg", "bd"])
    )

    kwargs = {}
    if self._within is not None:
      kwargs["from_"] = self._within[0]
      kwargs["to"] = self._within[1]
    if self._step is not None:
      kwargs["increment"] = self._step
    if self._format is not None:
      kwargs["format"] = self._format
    if self._placeholder is not None:
      kwargs["placeholder"] = self._placeholder
    if self._placeholder_color is not None:
      kwargs["placeholderforeground"] = self._placeholder_color
    if self._stepper_width is not None:
      kwargs["width"] = self._stepper_width

    self.widget = tkinter.ttk.Spinbox(
      parent_widget,
      textvariable = self.variable,
      style = self._style_id,
      wrap = self._wrap if self._wrap is not None else False,
      # command = lambda *_: self._callback_change(self, self.variable),
      **kwargs,
      **self._make_kwargs(["cursor", "width", "font", "justify"])
    )
    self._place_widget(self.widget, parent_uiitem, ["fill"])
    self._set_widget_id()

    self.variable.trace_add("write", lambda *_: self._callback_change(self, self.variable))
    self.widget.bind("<KeyPress-Return>", lambda *_: self._callback_submit(self, self.variable))
    return self.widget


class Image (UIItem):
  """ An image UI item that displays an image.

  This class creates a Label widget that displays an image. The Image can be configured with background color, padding, and other properties inherited from the UIItem base class. The layout method is responsible for creating the Label widget and placing it within its parent widget. The image can be specified as a file path, a tkinter.PhotoImage object, or a name of a Tkinter image that has been previously loaded. The _generate_image method is used to load the image and set the width and height of the Image UI item based on the dimensions of the loaded image.
  """

  def __init__(self, *, image: tkinter._Image | str | None = None, name: str | None = None) -> None:
    """ Initialize an Image instance.

    Args:
      image: The image to display in the Image UI item. This can be specified as a file path (string), a tkinter.PhotoImage object, or None. If a file path is provided, the image will be loaded from the specified file. If a tkinter.PhotoImage object is provided, it will be used directly as the image to display. If None is provided, no image will be displayed.
      name: An optional name of a Tkinter image that has been previously loaded. If provided, the image with this name will be used for the Image UI item. This allows for reusing images that have already been loaded into Tkinter by referencing them by name.
    """
    super().__init__()
    self.image = image
    self.tk_name = name

  def _generate_image(self) -> tkinter._Image:
    """ Internal method to load the image and set the width and height of the Image UI item based on the dimensions of the loaded image.

    Returns:
      The loaded image as a tkinter._Image object.
    """
    if isinstance(self.image, str):
      self.image = tkinter.PhotoImage(file = self.image)
    if self.tk_name is not None:
      self.image = tkinter.PhotoImage(name = self.tk_name)
    if self.image is None:
      raise ValueError("Image is not loaded.")
    self.width = self.image.width()
    self.height = self.image.height()
    return self.image

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Label:
    """ Layout the image within its parent widget.

    Args:
      parent_widget: The parent widget to which the image will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the image does not have its own background color specified.

    Returns:
      The Tkinter Label widget representing the image.
    """
    self._inherit_background(parent_uiitem)

    self.image = self._generate_image()

    self.widget = tkinter.Label(
      parent_widget,
      image = self.image,
      **self._make_kwargs(["bg", "bd", "cursor", "highlight", "justify", "anchor"])
    )

    self._place_widget(self.widget, parent_uiitem, ["padxy", "fill"])
    return self.widget

class ImagePNG (Image):
  """ An image UI item that displays a PNG image.

  This class inherits from Image and overrides the _generate_image method to load a PNG image using the PIL library. The layout method is responsible for creating the Label widget and placing it within its parent widget, just like in the Image class. The _generate_image method loads the PNG image from the specified file path, resizes it if necessary based on the frame width and height, and converts it to a format that can be displayed in a Tkinter Label widget.
  """

  def __init__(self, *, image: str):
    """ Initialize an ImagePNG instance.

    Args:
      image: The file path of the PNG image to display in the ImagePNG UI item. This should be a string representing the path to the PNG image file. The image will be loaded from this file path and displayed in the ImagePNG UI item.
    """
    super().__init__(image = image)

  def _generate_image(self) -> tkinter._Image:
    """ Internal method to load the PNG image using the PIL library, resize it if necessary, and convert it to a format that can be displayed in a Tkinter Label widget.

    Returns:
      The loaded and processed image as a tkinter._Image object that can be displayed in a Tkinter Label widget.
    """
    self._pil_img = PIL.Image.open(cast(str, self.image))

    if self._frame_width is not None and self._frame_height is not None:
      self._pil_img = self._pil_img.resize((self._frame_width, self._frame_height))
    elif self._frame_width is not None:
      target_height = int(self._pil_img.height * self._frame_width / self._pil_img.width)
      self._pil_img = self._pil_img.resize((self._frame_width, target_height))
    elif self._frame_height is not None:
      target_width = int(self._pil_img.width * self._frame_height / self._pil_img.height)
      self._pil_img = self._pil_img.resize((target_width, self._frame_height))

    self.image = PIL.ImageTk.PhotoImage(self._pil_img)
    super()._generate_image()
    return self.image

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Label:
    """ Layout the PNG image within its parent widget.

    Args:
      parent_widget: The parent widget to which the PNG image will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the PNG image does not have its own background color specified.
    """
    # self._generate_image()
    return super().layout(parent_widget, parent_uiitem)

class ImageSVG (Image):
  """ An image UI item that displays an SVG image.

  This class inherits from Image and overrides the _generate_image method to load an SVG image using the tkinter.PhotoImage class with the appropriate format option. The layout method is responsible for creating the Label widget and placing it within its parent widget, just like in the Image class. The _generate_image method loads the SVG image from the specified file path, resizes it if necessary based on the frame width and height, and converts it to a format that can be displayed in a Tkinter Label widget.
  """

  def __init__(self, *, image: str):
    """ Initialize an ImageSVG instance.

    Args:
      image: The file path of the SVG image to display in the ImageSVG UI item. This should be a string representing the path to the SVG image file. The image will be loaded from this file path and displayed in the ImageSVG UI item.
    """
    super().__init__(image = image)

  def _generate_image(self) -> tkinter._Image:
    """ Internal method to load the SVG image using the tkinter.PhotoImage class with the appropriate format option, resize it if necessary, and convert it to a format that can be displayed in a Tkinter Label widget.

    Returns:
      The loaded and processed image as a tkinter._Image object that can be displayed in a Tkinter Label widget.
    """
    # print("gen")
    if isinstance(self.image, str):
      self.image = tkinter.PhotoImage(file = self.image)

    if self._frame_width is not None:
      self.image.configure( format = f"svg -scaletowidth {self._frame_width}" )
      self._frame_width = None
    if self._frame_height is not None:
      self.image.configure( format = f"svg -scaletoheight {self._frame_height}" )
      self._frame_height = None

    super()._generate_image()
    return self.image

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Label:
    """ Layout the SVG image within its parent widget.

    Args:
      parent_widget: The parent widget to which the SVG image will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the SVG image does not have its own background color specified.
    """
    self._generate_image()
    return super().layout(parent_widget, parent_uiitem)


class Button (UIItem):
  """ A button UI item that can display text and/or an image, and can be clicked to perform an action.

  This class creates a Button widget that can display text and/or an image, and can be clicked to perform an action. The Button can be configured with background color, foreground color, font, padding, and other properties inherited from the UIItem base class. The onActive method allows for setting a callback function that will be called when the button is clicked. The width method allows for setting the width of the button in characters or pixels, depending on whether an image is included. The layout method is responsible for creating the Button widget and placing it within its parent widget.
  """

  def __init__(self, *, text: str | None = None, image: tkinter._Image | Image | str | None = None, imagePosition: Literal["center", "top", "bottom", "left", "right"] | None = None) -> None:
    """ Initialize a Button instance.

    Args:
      text: The text to display on the button.
      image: The image to display on the button.
      imagePosition: The position of the image relative to the text.
    """
    super().__init__()
    self.text = text
    self._image = image
    self._button_width: Optional[int] = None
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None
    self._image_position = imagePosition
    self._callback_command: Callable[[Button], Any] = lambda *_: None

  def onActive(self, callback: Callable[[Button], Any]) -> Self:
    """ Set a callback function that will be called when the button is clicked.

    Args:
      callback: A function that takes one argument, the Button instance itself. This function will be called when the button is clicked.
    """
    self._callback_command = callback
    return self

  def width(self, width: int) -> Self:
    """ Set the width of the button.

    If an image is included, the width is set in pixels. If no image is included, the width is set in terms of the number of characters that can fit in the button using an average monospaced font.

    Args:
      width: The width of the button. If an image is included, this should be the width in pixels. If no image is included, this should be the number of characters that can fit in the button.
    """
    self._button_width = width
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Button:
    """ Layout the button within its parent widget.

    Args:
      parent_widget: The parent widget to which the button will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the button does not have its own background color specified.

    Returns:
      The Tkinter Button widget representing the button.
    """
    self._inherit_background(parent_uiitem)

    self._style = tkinter.ttk.Style(parent_widget)
    self._style_id = random_string(12)
    self._style.configure(
      f"{self._style_id}.TButton",
      **self._make_kwargs(["bg", "fg", "font"])
    )

    kwargs = {}
    kwargs["text"] = self.text if self.text is not None else ""
    if self._image is not None:
      if isinstance(self._image, Image):
        self._image = self._image._generate_image()
      # elif isinstance(self.image, str):
      #   self.image = tkinter.PhotoImage(file = self.image)
      kwargs["image"] = self._image
    if self._image is not None:
      kwargs["compound"] = self._image_position if self._image_position is not None else "left"
    if self._button_width is not None:
      kwargs["width"] = self._button_width
    if self._callback_command is not None:
      kwargs["command"] = lambda: self._callback_command(self)

    self.widget = tkinter.ttk.Button(
      parent_widget,
      style = f"{self._style_id}.TButton",
      **kwargs,
      **self._make_kwargs(["cursor", "justify", "anchor"])
    )
    self._place_widget(self.widget, parent_uiitem, ["fill", "padxy"])
    return self.widget

class CheckBox (UIItem):
  """ A checkbox UI item that allows the user to toggle a boolean value.

  This class creates a Checkbutton widget that allows the user to toggle a boolean value. The CheckBox can be configured with background color, foreground color, font, padding, and other properties inherited from the UIItem base class. The onChanged method allows for setting a callback function that will be called whenever the value of the CheckBox changes. The layout method is responsible for creating the Checkbutton widget and placing it within its parent widget. The variable argument in the constructor is a tkinter.BooleanVar that will be used to store the current value of the CheckBox, and it will be updated automatically as the user toggles the CheckBox. The text argument in the constructor specifies the label to display next to the CheckBox. The _callback_change function is called whenever the value of the CheckBox changes, and it receives the CheckBox instance and the tkinter.BooleanVar as arguments, allowing for custom behavior to be implemented when the CheckBox is toggled.
  You cannot set an image for CheckBox, as it is not supported in this implementation.
  """

  def __init__(self, variable: tkinter.BooleanVar, /, *, text: str) -> None:
    """ Initialize a CheckBox instance.

    Args:
      variable: A tkinter.BooleanVar that will be used to store the current value of the CheckBox. This variable will be updated automatically as the user toggles the CheckBox.
      text: The label to display next to the CheckBox. This is a string that will be displayed as the text label for the CheckBox, providing a description of what the CheckBox represents or what it is used for.
    """
    super().__init__()
    self.variable = variable
    self.text = text
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None
    self._callback_change: Callable[[CheckBox, tkinter.BooleanVar], Any] = lambda *_: None

  def onChanged(self, callback: Callable[[CheckBox, tkinter.BooleanVar], Any]) -> Self:
    """ Set a callback function that will be called whenever the value of the CheckBox changes.

    Args:
      callback: A function that takes two arguments: the CheckBox instance and the tkinter.BooleanVar that contains the current value of the CheckBox. This function will be called whenever the value of the CheckBox changes, either due to user input or programmatically.
    """
    self._callback_change = callback
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Checkbutton:
    """ Layout the checkbox within its parent widget.

    Args:
      parent_widget: The parent widget to which the checkbox will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the checkbox does not have its own background color specified.

    Returns:
      The Tkinter Checkbutton widget representing the checkbox.
    """
    self._inherit_background(parent_uiitem)

    self._style = tkinter.ttk.Style(parent_widget)
    self._style_id = f"{random_string(12)}.TCheckbutton"
    self._style.configure(
      self._style_id,
      **self._make_kwargs(["bg", "fg", "font"])
    )

    self.widget = tkinter.ttk.Checkbutton(
      parent_widget,
      text = self.text,
      variable = self.variable,
      **self._make_kwargs(["cursor"])
    )
    self._place_widget(self.widget, parent_uiitem, ["fill", "padxy"])
    self._set_widget_id()

    self.variable.trace_add("write", lambda *_: self._callback_change(self, self.variable))
    return self.widget


class Canvas (UIItem):
  """ A canvas UI item that allows for drawing shapes, images, and other graphical elements.

  This class creates a Canvas widget that allows for drawing shapes, images, and other graphical elements. The Canvas can be configured with background color, padding, and other properties inherited from the UIItem base class. The layout method is responsible for creating the Canvas widget and placing it within its parent widget. If the scrollable argument is set to True, horizontal and vertical scrollbars will be added to the Canvas to allow for scrolling when the content exceeds the visible area of the Canvas. The highlightthickness of the Canvas is set to 0 to remove the default border around the Canvas.
  """

  def __init__(self, width: int, height: int, scrollable: bool = False) -> None:
    """ Initialize a Canvas instance.

    Args:
      width: The width of the Canvas in pixels. This determines how wide the Canvas will be when it is displayed in the UI.
      height: The height of the Canvas in pixels. This determines how tall the Canvas will be when it is displayed in the UI.
      scrollable: A boolean that determines whether the Canvas should include scrollbars when the content exceeds the visible area. If True, horizontal and vertical scrollbars will be added to the Canvas to allow for scrolling. If False, no scrollbars will be added, and the content will be clipped to the visible area of the Canvas. The default is False.
    """
    super().__init__()
    self._width = width
    self._height = height
    self._scrollable = scrollable

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Canvas:
    """ Layout the canvas within its parent widget.

    Args:
      parent_widget: The parent widget to which the canvas will be added.
      parent_uiitem: The parent UI item, if any. This is mainly used for inheriting the background color if the canvas does not have its own background color specified.
    """
    self._inherit_background(parent_uiitem)

    self.widget = tkinter.Canvas(
      parent_widget,
      width = self._width,
      height = self._height,
      takefocus = 1,
      **self._make_kwargs(["bg", "cursor", "highlight"])
    )
    if self._scrollable:
      self._h_scrollbar = tkinter.Scrollbar(parent_widget, orient = tkinter.HORIZONTAL, command = self.widget.xview)
      self._v_scrollbar = tkinter.Scrollbar(parent_widget, orient = tkinter.VERTICAL, command = self.widget.yview)
      self.widget.configure(xscrollcommand = self._h_scrollbar.set, yscrollcommand = self._v_scrollbar.set)
      self._h_scrollbar.pack(side = tkinter.BOTTOM, fill = tkinter.X)
      self._v_scrollbar.pack(side = tkinter.RIGHT, fill = tkinter.Y)

    self._place_widget(self.widget, parent_uiitem, ["padxy", "fill"])
    return self.widget


class WidgetVar():
  """ A helper class that allows for storing a reference to a UIItem instance.

  This class is used to store a reference to a UIItem instance, allowing for easy access to the UIItem from other parts of the code. The value property can be set to a UIItem instance, and it can be accessed later to retrieve the stored UIItem. This is particularly useful in callback functions or event handlers where you may need to access the UIItem that triggered the event or that is associated with a particular action.
  """

  def __init__(self) -> None:
    """ Initialize a WidgetVar instance. The value is initially set to None, indicating that it does not currently reference any UIItem instance.
    """
    self.__value: Optional[UIItem] = None

  @property
  def value(self) -> Optional[UIItem]:
    """ Get the current value of the WidgetVar, which is a reference to a UIItem instance.

    Returns:
      The current value of the WidgetVar, which is a reference to a UIItem instance. If the value has not been set, it will return None.
    """
    return self.__value

  @value.setter
  def value(self, target: UIItem) -> None:
    """ Set the value of the WidgetVar to reference a specific UIItem instance.

    Args:
      target: The UIItem instance that the WidgetVar should reference. This will allow for easy access to this UIItem instance from other parts of the code by accessing the value property of the WidgetVar.
    """
    self.__value = target
