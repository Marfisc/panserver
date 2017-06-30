# Panserver

Panserver is a very simple HTTP server written in Python to view rendered [Markdown](https://en.wikipedia.org/wiki/Markdown) documents.
It is not intended to be used as web-facing server. Instead it is a helper to view Markdown locally. For rendering [`pandoc`](http://pandoc.org/) is employed, which must be installed. The Python library [bottle](https://bottlepy.org/docs/dev/) must be installed as well.

## Usage

Run `python panserver.py [-a]` in the directory of files. Open `localhost:8080/view/nameofmarkdown`. There you will see your document in rendered form. If `-a` was specified, it will auto-update when you save the Markdown file!
