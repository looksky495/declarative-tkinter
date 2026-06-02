# Author: looksky495 <looksky603@gmail.com>
# Copyright (c) 2026 looksky495. All rights reserved.
# License: MIT License. See LICENSE file in the project root for full license information.

from setuptools import setup, find_packages
import declarative_tkinter

VERSION = declarative_tkinter.__version__

INSTALL_REQUIRES = [
  "Pillow>=12.0.0"
]

CLASSIFIERS = [
  "Development Status :: 3 - Alpha",                              # 開発ステータス
  "Intended Audience :: Developers",                              # 対象読者（開発者向け）
  "License :: OSI Approved :: MIT License",                       # ライセンス
  "Programming Language :: Python :: 3",                          # 使用言語
  "Programming Language :: Python :: 3.14",                       # 動作確認しているバージョン
  "Topic :: Software Development :: Libraries :: Python Modules", # トピック分類
  "Topic :: Software Development :: User Interfaces",             # GUIライブラリ
]

with open("README.md", "r", encoding="utf-8") as f:
  LONG_DESCRIPTION = f.read()

setup(
  name = "declarative-tkinter",
  author = "looksky495",
  author_email = "looksky603@gmail.com",
  maintainer = "looksky495",
  maintainer_email = "looksky603@gmail.com",
  description = "A declarative GUI library for Python's Tkinter.",
  long_description = LONG_DESCRIPTION,
  long_description_content_type = "text/markdown",
  license = "MIT",
  url = "https://github.com/looksky495/declarative-tkinter",
  version = VERSION,
  download_url = "https://github.com/looksky495/declarative-tkinter",
  python_requires = ">=3.14",
  install_requires = INSTALL_REQUIRES,
  packages = find_packages(),
  classifiers = CLASSIFIERS,
)
