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
  global _BlankImage
  if _BlankImage is None:
    _BlankImage = PIL.ImageTk.PhotoImage(PIL.Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
  return _BlankImage

def random_string(length: int) -> str:
  return random.choice(string.ascii_letters) + ''.join(random.choice(string.ascii_letters + string.digits) for i in range(length - 1))


class UIColor:
  def __init__(self, r: float, g: float, b: float, max: float = 255) -> None:
    self.__r = r
    self.__g = g
    self.__b = b
    self.__max = max

  def __str__(self) -> str:
    hex_r = f"{int(self.__r / self.__max * 255):0>2x}"
    hex_g = f"{int(self.__g / self.__max * 255):0>2x}"
    hex_b = f"{int(self.__b / self.__max * 255):0>2x}"
    return f"#{hex_r}{hex_g}{hex_b}"

_UIColor = str | UIColor

def _decide_side(uiitem: UIItem | None):
  if isinstance(uiitem, HStack):
    return tkinter.LEFT
  else:
    return tkinter.TOP


class UIItem():
  def __init__(self) -> None:
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
    self._name = name
    return self

  def getUIByName(self, name: str) -> Optional[UIItem]:
    if self._name == name:
      return self
    for item in self.contents:
      searched = item.getUIByName(name)
      if searched is not None:
        return searched

  def takeout(self, *, out: WidgetVar) -> Self:
    out.value = self
    return self

  @abstractmethod
  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Widget: ...

  def _make_kwargs(self, args: list[str]) -> dict:
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
    """ Inherit background color from parent UIItem """
    if self._background_color is None:
      self._background_color = parent_uiitem._background_color if parent_uiitem else None

  def _place_widget(self, widget: tkinter.Widget, parent_uiitem: UIItem | None, kwargs: list[str]) -> None:
    if not self._is_hidden:
      widget.bind("<Button-1>", lambda event: self._callback_clicked(self, event))
      widget.bind("<Enter>", lambda event: self._callback_mouse_enter(self, event))
      widget.bind("<Leave>", lambda event: self._callback_mouse_leave(self, event))

    self.parent_uiitem = parent_uiitem

    if not isinstance(parent_uiitem, Grid):
      # pack
      widget.pack(side = _decide_side(parent_uiitem), **self._make_kwargs(kwargs))
    else:
      "gridはここで配置しない（GridRowに処理を任せる）"
    self._set_widget_id()
    self._is_hidden = False

  def _set_widget_id(self) -> None:
    if self.widget is not None:
      self._id = self.widget.winfo_id()
    else:
      raise ValueError("Widget is not set.")

  def hide(self) -> None:
    """ ウィジェットを非表示にする """
    if self.widget is not None and not self._is_hidden:
      if isinstance(self.parent_uiitem, Grid):
        self.widget.grid_remove()
      else:
        self.widget.pack_forget()
    self._is_hidden = True


  def padding(self, all: Optional[int] = None, /, *, vertical: Optional[int] = None, horizontal: Optional[int] = None) -> Self:
    if all is not None:
      self._padding_pady = all
      self._padding_padx = all
    if vertical is not None:
      self._padding_pady = vertical
    if horizontal is not None:
      self._padding_padx = horizontal
    return self

  def borderWidth(self, width: int, /) -> Self:
    if width is not None:
      self._border_width = width
    return self

  def focusBorder(self, *, backColor: Optional[_UIColor] = None, focusColor: Optional[_UIColor] = None, width: Optional[int] = 1) -> Self:
    if backColor is not None:
      self._highlight_back_color = str(backColor)
    if focusColor is not None:
      self._highlight_focus_color = str(focusColor)
    if width is not None:
      self._highlight_width = width
    return self

  def foregroundColor(self, color: _UIColor) -> Self:
    self._foreground_color = str(color)
    return self

  def backgroundColor(self, color: Optional[_UIColor] = None) -> Self:
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
    self._fill_direction = direction
    self._fill_expand = expand
    return self

  def pointer(self, cursor_type: str) -> Self:
    self._cursor_type = cursor_type
    return self

  def frame(self, *, width: Optional[int] = None, height: Optional[int] = None) -> Self:
    if width is not None:
      self._frame_width = width
    if height is not None:
      self._frame_height = height
    return self

  def font(self, fontDescription: tkinter.font._FontDescription, /) -> Self:
    self._font = fontDescription
    return self

  def alignment(self, anchor: Literal["n", "ne", "e", "se", "s", "sw", "w", "nw", "center", "leading", "trailing"]) -> Self:
    if anchor == "leading":
      anchor = "w"
    if anchor == "trailing":
      anchor = "e"
    self._anchor = anchor
    return self

  def justify(self, justify: Literal["left", "center", "right"]) -> Self:
    self._justify = justify
    return self

  def onClicked(self, callback: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any]) -> Self:
    self._callback_clicked = callback
    return self

  def onMouseEnter(self, callback: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any]) -> Self:
    self._callback_mouse_enter = callback
    return self

  def onMouseLeave(self, callback: Callable[[UIItem, tkinter.Event[tkinter.Misc]], Any]) -> Self:
    self._callback_mouse_leave = callback
    return self

  def splitWeight(self, weight: int) -> Self:
    """ For VSplitView """
    self._split_weight = weight
    return self

  def rowSpan(self, span: int) -> Self:
    """ For Grid """
    if span < 1 or not isinstance(span, int):
      raise ValueError("span must be positive integer.")
    self._row_span = span
    return self

  def columnSpan(self, span: int) -> Self:
    """ For Grid """
    if span < 1 or not isinstance(span, int):
      raise ValueError("span must be positive integer.")
    self._column_span = span
    return self

  def disable(self, flag: bool = True):
    """ 有効・無効を切り替える """
    self._is_disabled = not not flag
    if self.widget is not None:
      self.widget["state"] = tkinter.DISABLED if self._is_disabled else tkinter.NORMAL


class Rectangle (UIItem):
  def __init__(self, *, width: int, height: int) -> None:
    super().__init__()
    self.width = width
    self.height = height

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Frame:
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
  def __init__(self, *contents: UIItem) -> None:
    super().__init__()
    self.contents = contents

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Frame:
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
    if self.widget is None:
      raise ValueError("VStack widget is not yet created.")
    widget = item.layout(self.widget, self)
    self.contents += (item,)
    return widget

class HStack (VStack): ...

class VSplitView (UIItem):
  def __init__(self, *contents: UIItem) -> None:
    super().__init__()
    self.contents = contents
    self._sash_width: int = 3
    self._sash_color: Optional[str] = None
    self._border_color: Optional[str] = None
    self._orient: Literal["horizontal", "vertical"] = tkinter.HORIZONTAL
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None

  def sashWidth(self, width: int) -> Self:
    self._sash_width = width
    return self

  def sashColor(self, color: _UIColor) -> Self:
    self._sash_color = str(color)
    return self

  def borderColor(self, color: _UIColor) -> Self:
    self._border_color = str(color)
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.PanedWindow:
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
  def __init__(self, *contents: UIItem) -> None:
    super().__init__(*contents)
    self._orient = tkinter.HORIZONTAL


class GridRow:
  def __init__(self, *contents: UIItem) -> None:
    self.contents = contents
    self._column_index: int = 0
    # 予約済みの列番号
    self._reserved_columns: list[int] = []

  def layout(self, parent_widget: tkinter.Frame, parent_uiitem: Grid) -> None:
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
  def __init__(self, *contents: GridRow) -> None:
    super().__init__()
    self.rows: tuple[GridRow, ...] = contents
    self._row_index: int = 0

  def getUIByName(self, name: str) -> Optional[UIItem]:
    if self._name == name:
      return self
    for row in self.rows:
      for item in row.contents:
        searched = item.getUIByName(name)
        if searched is not None:
          return searched
    return None

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Frame:
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
  def __init__(self, *contents: tuple[str, UIItem]) -> None:
    super().__init__()
    self.tabs: tuple[tuple[str, UIItem], ...] = contents
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None
    self._border_color: Optional[str] = None
    self._tab_background_color: Optional[str] = None

  def getUIByName(self, name: str) -> Optional[UIItem]:
    if self._name == name:
      return self
    for item in self.tabs:
      searched = item[1].getUIByName(name)
      if searched is not None:
        return searched
    return None

  def borderColor(self, color: _UIColor) -> Self:
    self._border_color = str(color)
    return self

  def tabBackgroundColor(self, color: _UIColor) -> Self:
    self._tab_background_color = str(color)
    return self

  def paddingOutside(self, all: int | None = None, /, *, vertical: int | None = None, horizontal: int | None = None, top: int | None = None, leading: int | None = None, bottom: int | None = None, trailing: int | None = None) -> Self:
    """ For ttk Widgets """
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
  def __init__(self, orientation: Optional[Literal["horizontal", "vertical"]] = None) -> None:
    super().__init__()
    self._orientation: Optional[Literal["horizontal", "vertical"]] = orientation
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None
    self.fill("both")

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Separator:
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
  """ a.k.a. &lt;p /&gt; """
  def __init__(self, text: str) -> None:
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
    if isinstance(self.widget, tkinter.Label):
      self.widget.configure(text = text)
    self.text = text

class TextField (UIItem):
  def __init__(self, variable: tkinter.StringVar, /, *, placeholder: Optional[str] = None) -> None:
    super().__init__()
    self.variable = variable
    self.placeholder = placeholder
    self.is_secure = False
    self._style: Optional[tkinter.ttk.Style] = None
    self._placeholder_color: Optional[str] = None
    self._callback_change: Callable[[TextField, tkinter.StringVar], Any] = lambda *_: None
    self._callback_submit: Callable[[TextField, tkinter.StringVar], Any] = lambda *_: None

  def width(self, width: int) -> Self:
    self._frame_width = width
    return self

  def placeholderColor(self, color: _UIColor) -> Self:
    self._placeholder_color = str(color)
    return self

  def onChange(self, callback: Callable[[TextField, tkinter.StringVar], Any]) -> Self:
    self._callback_change = callback
    return self

  def onSubmit(self, callback: Callable[[TextField, tkinter.StringVar], Any]) -> Self:
    self._callback_submit = callback
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Entry:
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
  def __init__(self, variable: tkinter.StringVar, /, *, placeholder: Optional[str] = None) -> None:
    super().__init__(variable, placeholder = placeholder)
    self.is_secure = True

_TextWidgets = tkinter.Text | tkinter.scrolledtext.ScrolledText

class TextEditor (UIItem):
  def __init__(self, /, *, wrap: Literal["none", "char", "word"] = "word", scrollable: bool = True) -> None:
    super().__init__()
    self._wrap: Literal["none", "char", "word"] = wrap
    self._scrollable = scrollable
    self._callback_change: Callable[[tkinter.Event[_TextWidgets], TextEditor], Any] = lambda *_: None

  def width(self, width: int) -> Self:
    self._frame_width = width
    return self

  def height(self, height: int) -> Self:
    self._frame_height = height
    return self

  def onChange(self, callback: Callable[[tkinter.Event[_TextWidgets], TextEditor], Any]) -> Self:
    self._callback_change = callback
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Text:
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
    self.widget: tkinter.Text # type: ignore
    if self.widget.edit_modified():
      self._callback_change(event, self)
    self.widget.edit_modified(False)


StepperT = TypeVar("StepperT", bound = tkinter.Variable)

class Stepper (UIItem, Generic[StepperT]):
  def __init__(self, variable: StepperT, /, *, within: tuple[float, float] | None = None, step: float | None = None, placeholder: str | None = None, wrap: bool | None = None) -> None:
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
    self._callback_change = callback
    return self

  def onSubmit(self, callback: Callable[[Stepper[StepperT], StepperT], Any]) -> Self:
    self._callback_submit = callback
    return self

  def placeholderColor(self, color: _UIColor) -> Self:
    self._placeholder_color = str(color)
    return self

  def format(self, fmt: str) -> Self:
    self._format = fmt
    return self

  def width(self, width: int) -> Self:
    """ 平均的な等幅フォントの文字数ぶんの幅を指定 """
    self._stepper_width = width
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Spinbox:
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
  def __init__(self, *, image: tkinter._Image | str | None = None, name: str | None = None) -> None:
    super().__init__()
    self.image = image
    self.tk_name = name

  def _generate_image(self) -> tkinter._Image:
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
  def __init__(self, *, image: str):
    super().__init__(image = image)

  def _generate_image(self) -> tkinter._Image:
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
    # self._generate_image()
    return super().layout(parent_widget, parent_uiitem)

class ImageSVG (Image):
  def __init__(self, *, image: str):
    super().__init__(image = image)

  def _generate_image(self) -> tkinter._Image:
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
    self._generate_image()
    return super().layout(parent_widget, parent_uiitem)


class Button (UIItem):
  def __init__(self, *, text: str | None = None, image: tkinter._Image | Image | str | None = None, imagePosition: Literal["center", "top", "bottom", "left", "right"] | None = None) -> None:
    super().__init__()
    self.text = text
    self._image = image
    self._button_width: Optional[int] = None
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None
    self._image_position = imagePosition
    self._callback_command: Callable[[Button], Any] = lambda *_: None

  def onActive(self, callback: Callable[[Button], Any]) -> Self:
    self._callback_command = callback
    return self

  def width(self, width: int) -> Self:
    """ ボタンの幅を設定します。

    画像が含まれている場合、単位はpxになります。
    画像が含まれていない場合、平均的な等幅フォントの文字数ぶんの幅になります。
    """
    self._button_width = width
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Button:
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
  def __init__(self, variable: tkinter.BooleanVar, /, *, text: str) -> None:
    """ 画像未対応 """
    super().__init__()
    self.variable = variable
    self.text = text
    self._style: Optional[tkinter.ttk.Style] = None
    self._style_id: Optional[str] = None
    self._callback_change: Callable[[CheckBox, tkinter.BooleanVar], Any] = lambda *_: None

  def onChanged(self, callback: Callable[[CheckBox, tkinter.BooleanVar], Any]) -> Self:
    self._callback_change = callback
    return self

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.ttk.Checkbutton:
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
  """ highlighttickness は 0 に設定されます。 """
  def __init__(self, width: int, height: int, scrollable: bool = False) -> None:
    super().__init__()
    self._width = width
    self._height = height
    self._scrollable = scrollable

  def layout(self, parent_widget: tkinter.Misc, parent_uiitem: UIItem | None = None) -> tkinter.Canvas:
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
  def __init__(self) -> None:
    self.__value: Optional[UIItem] = None

  @property
  def value(self) -> Optional[UIItem]:
    return self.__value

  @value.setter
  def value(self, target: UIItem) -> None:
    self.__value = target
