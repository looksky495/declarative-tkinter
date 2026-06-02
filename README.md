# declarative-tkinter

A small declarative UI layer on top of Python's Tkinter — inspired by SwiftUI-style composition.

This project is **Alpha**. APIs may change.

**Note**: this document is written by AI and may contain inaccuracies, because this library origianlly developed as a part of my homework for the academic source.

## Features

- Compose UI as a tree (`VStack`, `HStack`, `Grid`, `TabView`, ...)
- Chainable styling and event handlers (`padding`, `fill`, `onClicked`, ...)
- App/window primitives (`App`, `Window`) and a simple menu API (`Menu`)

## Requirements

- Python `>= 3.14`
- Tk `>= 9.0`
- Dependency: `Pillow>=12.0.0`

Note: importing `declarative_tkinter` performs runtime checks for Python/Tk versions and raises `RuntimeError` when the requirements are not met.

## Installation

```bash
pip install declarative-tkinter
```

Editable install for development:

```bash
pip install -e .
```

## Quick start

Create an `App`, create a `Window`, lay out a component tree into `window.window`, then call `app.ready()`.

```python
from declarative_tkinter import App, Window
from declarative_tkinter.component import VStack, Text, Button


def main() -> None:
	app = App()
	window = Window(app, width=360, height=180)
	window.set_title("declarative-tkinter")

	ui = VStack(
		Text("Hello, Tkinter!"),
		Button(text="Quit").onActive(lambda _btn: app.quit()),
	).padding(12)

	ui.layout(window.window)
	app.ready()


if __name__ == "__main__":
	main()
```

## Components (excerpt)

Most components live in `declarative_tkinter.component`.

- Layout: `VStack`, `HStack`, `Grid`, `GridRow`, `VSplitView`, `HSplitView`, `TabView`
- Display: `Text`, `Image`, `ImagePNG`, `ImageSVG`, `Separator`, `Rectangle`
- Input: `TextField`, `SecureField`, `TextEditor`, `Stepper`, `CheckBox`
- Other: `Canvas`

Common chainable helpers include:

- `padding(...)`, `fill("x"|"y"|"both", expand=...)`
- `foregroundColor(...)`, `backgroundColor(...)`
- `borderWidth(...)`, `focusBorder(...)`
- `frame(width=..., height=...)`, `font(...)`, `alignment(...)`, `justify(...)`
- `onClicked(...)`, `onMouseEnter(...)`, `onMouseLeave(...)`

## TextField example

`TextField` uses a `tkinter.StringVar` and supports `onChange` / `onSubmit` callbacks.

```python
import tkinter

from declarative_tkinter import App, Window
from declarative_tkinter.component import VStack, Text, TextField, Button


def main() -> None:
	app = App()
	window = Window(app, width=420, height=220)
	window.set_title("TextField demo")

	name = tkinter.StringVar(value="")
	message = Text("(empty)")

	ui = VStack(
		TextField(name, placeholder="Your name")
			.onSubmit(lambda _tf, var: message.setText(f"Hello, {var.get()}!")),
		message,
		Button(text="Quit").onActive(lambda _btn: app.quit()),
	).padding(12)

	ui.layout(window.window)
	app.ready()


if __name__ == "__main__":
	main()
```

## Real-world layout example (Grapher-like editor shell)

When your UI looks like an “app shell” (toolbar + sidebars + a main canvas + a status bar), plain Tkinter tends to become a long sequence of `Frame(...)`, `pack(...)`, and widget wiring.

With `declarative-tkinter`, you can describe the layout as a single tree and attach behavior where it belongs:

```python
import tkinter
import tkinter.font

from declarative_tkinter import App, Window
from declarative_tkinter.component import VStack, HStack, Text, TextField, Canvas, Separator


def main() -> None:
	app = App()
	window = Window(app, width=1000, height=700)
	window.set_title("Editor shell demo")

	command = tkinter.StringVar(value="")
	status = Text("Ready").name("status")

	body = VStack(
		# Top command bar
		HStack(
			Text("Command").padding(horizontal=8),
			TextField(command, placeholder="Type a command and press Enter")
				.padding(horizontal=8, vertical=4)
				.focusBorder(backColor="#717171", focusColor="#6889f6", width=2)
				.font(tkinter.font.Font(family=("Menlo"), size=10))
				.fill("x", expand=True)
				.onSubmit(lambda _tf, var: status.setText(f"Executed: {var.get().strip()}")),
		).frame(height=30).fill("x").backgroundColor("#2C2C2C"),

		# Main area
		HStack(
			# Left toolbar
			VStack(
				Text("Move").padding(6).pointer("pointinghand")
					.onClicked(lambda _ui, _ev: status.setText("Mode: move")),
				Text("Select").padding(6).pointer("pointinghand")
					.onClicked(lambda _ui, _ev: status.setText("Mode: select")),
				Separator().padding(vertical=10),
			).frame(width=80).fill("y").backgroundColor("#3B3B3B"),

			# Center canvas (scrollable)
			VStack(
				Canvas(1, 1, scrollable=True)
					.fill("both", expand=True)
					.backgroundColor("#ffffff")
					.name("main_canvas"),
			).fill("both", expand=True).backgroundColor("#202020"),

			# Right sidebar (inspector)
			VStack(
				Text("Inspector").padding(8),
			).frame(width=260).fill("y").backgroundColor("#232323"),
		).fill("both", expand=True),

		# Status bar
		HStack(
			status.padding(vertical=6, horizontal=12),
		).frame(height=30).fill("x").backgroundColor("#0B3881"),
	).backgroundColor("#1E1E1E").fill("both", expand=True)

	body.layout(window.window)

	# Optional: access widgets later via name lookup
	canvas_item = body.getUIByName("main_canvas")
	if isinstance(canvas_item, Canvas) and isinstance(canvas_item.widget, tkinter.Canvas):
		canvas_item.widget.create_text(20, 20, text="Hello Canvas", anchor="nw")

	app.ready()


if __name__ == "__main__":
	main()
```

## Menu

Attach a menu to a window using `Window.set_menu()`.

```python
from declarative_tkinter import (
	App,
	Window,
	Menu,
	MenuSubmenu,
	MenuButton,
	MenuSeparator,
	Notification,
)


def main() -> None:
	app = App()
	window = Window(app, width=320, height=160)
	window.set_title("Menu demo")

	window.set_menu(
		Menu([
			MenuSubmenu(
				"File",
				items=[
					MenuButton(
						"Notify",
						click=lambda app: app.notify(Notification("declarative-tkinter", "Hello from Menu")),
					),
					MenuSeparator(),
					MenuButton("Quit", click=lambda app: app.quit(), accelerator="Cmd+Q"),
				],
			),
		])
	)

	app.ready()


if __name__ == "__main__":
	main()
```

## Platform notes

- `App.notify(...)` calls Tk's `sysnotify`. It may fail depending on platform configuration and will return `False`.
- Some `Window` APIs (e.g. `is_dark_mode`, `set_bounce`) are macOS-only.

## License

MIT
