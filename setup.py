# Author: looksky495 <looksky603@gmail.com>
# Copyright (c) 2026 looksky495. All rights reserved.
# License: MIT License. See LICENSE file in the project root for full license information.

from setuptools import setup, find_packages
import declarative_tkinter

VERSION = declarative_tkinter.__version__

INSTALL_REQUIRES = [
  "Pillow>=12.0.0"
]

PACKAGES = [
  "declarative_tkinter",
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