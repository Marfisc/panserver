# Panserver

Panserver is a very simple HTTP server written in Python 3 to view rendered [Markdown](https://en.wikipedia.org/wiki/Markdown) documents.
It is not intended to be used as web-facing server. Instead it is a helper to view Markdown locally. For rendering [`pandoc`](http://pandoc.org/) is employed, which must be installed. The Python library [bottle](https://bottlepy.org/docs/dev/) must be installed as well.

## Quick Start

Run the command

```
python panserver.py [-a] [-b] path
```

where `path` is the path to the directory of your document(s).

Now open `http://localhost:8080/` in a browser (which is done automatically if you specified the `-b` option). You will find an index of all Markdown documents in the directory. Click on a link to view the rendered documents. If `-a` was specified, the view will auto-refresh when you save the Markdown file!

## Usage

Command line (given `python` is Python 3):

```
python panserver.py [-a] [-b] [-p port] [path]
```

This starts a local http server. The Markdown conversion utility [`pandoc`](http://pandoc.org/) must installed and available on the path.
The python library [bottle](https://bottlepy.org/docs/dev/) must be installed and available as well.
No further dependencies or files are required; except for the mentioned dependencies, `panserver.py` is self-contained.

Hit `Ctrl-c` to stop the server.

### Path

A path to the to the document directory. If no path is specified the current working directory is used.
All files (not only Markdown documents) in the directory and all its subdirectories will be available through the server! This in necessary to allow you to link images (or scripts and stylesheets etc) in your documents. 

### Auto-refresh: `-a`

Specifying this option makes Panserver include a small script into the generated HTML. The script will constantly poll the server and refresh the page when the correspondig Markdown source file has been updated.

### Open browser: `-b`

If you specify this option, Panserver will open its index page in your standard web browser.

### Port: `-p number`

You can set the port Panserver should listen to with this option. The default is `8080`.

## Behaviour

When you start Panserver it will act as an HTTP server (on the given port).
On the same machine it will be available in a web browser as `http://localhost:8080/` (substitute `8080` with correct port if you specified it explicitely).

**Beware** that access is not restricted to the same machine!
All files (not only Markdown documents) in the document directory and all its subdirectories will be available through the server to whomever has access to the port on that machine!

### Index page

The index page is available at address `/` (that is `http://localhost:8080/` normally). It will list all markdown files in the document directory.

### Markdown views

The address `/view/<some_path>`, where `<some_path>` or `<some_path>.md` is a path relative to the document directory to a Markdown file, is a Markdown view page. It will display the output of `pandoc` for the given Markdown file plus some minimal styling.

### Other files

The address `/view/<some_path>`, where `<somepath>` is a path relative to the document directory to a non-Markdown file, will serve the file like a normal HTTP server would.

