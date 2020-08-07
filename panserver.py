#!/usr/bin/env python3

from bottle import route
import bottle
import tempfile
import os
import shutil
import subprocess
import json
import hashlib

def is_known_format(fmt):
    return fmt in ['std', 'export', 'simple', 'inline']

def get_out_filename(name, fmt = 'std'):
    if not is_known_format(fmt): raise Exception('Unknown format')
    f =  os.path.join(outdir, get_out_filename_rel(name, fmt))
    if not os.path.abspath(f).startswith(os.path.abspath(outdir)):
        raise Exception('Path out problem', os.path.abspath(f), os.path.abspath(outdir))
    return f

def get_out_filename_rel(name, fmt = 'std'):
    if not is_known_format(fmt): raise Exception('Unknown format')
    return "{}.{}.html".format(name, fmt)

def get_in_filename(name):
    f = os.path.join(indir, get_in_filename_rel(name))
    if not os.path.abspath(f).startswith(os.path.abspath(indir)):
        raise Exception('Path in problem', os.path.abspath(f), os.path.abspath(indir))
    for file_ending in [""] + file_endings:
        if os.path.exists(f + file_ending):
            return f + file_ending
    return f

def get_in_filename_rel(name):
    return name

def has_compile_file_ending(f):
    for file_ending in file_endings:
        if f.endswith(file_ending):
            return True
    return False

@route('/view/<name:path>')
def route_view(name):
    infile = get_in_filename(name)

    if os.path.exists(infile) and has_compile_file_ending(infile):
        fmt = bottle.request.query.fmt or "std"
        if not is_known_format(fmt): return 'Unknown format'

        compile_document(name, fmt)
        return bottle.static_file(get_out_filename_rel(name, fmt), outdir)

    else:
        return bottle.static_file(get_in_filename_rel(name), indir)

@route('/refresh/<name:path>')
def route_refresh(name):
    time = bottle.request.query.time
    try:
        if time is not None:
            time = int(time)
    except ValueError:
        time = None

    if time is not None:
        result = newer_input_exists(name, time)
    else:
        result = needs_update(name)

    if result:
        return "True"
    else:
        return "False"

@route('/generated/<name:path>')
def route_generated(name):
    return bottle.static_file(name, os.path.join(tempdir, "generated"))

@route('/')
def route_index():
    text = ""

    text += "<html><head><title>Panserver Index</title>"
    text += '<style type="text/css">{}</style>'.format(style_basic + style_index)
    text += "</head><body>"
    text += '<h1>Panserver</h1>'
    text += 'Serving Markdown documents rendered using <a href="http://pandoc.org/">pandoc</a>. By <a href="http://marcelfischer.eu/">Marcel Fischer</a>'

    def dir_entry(dirname, toplevel = False):
        #collect markdown files recursively into a list
        #return '' if no markdown file is in the directory
        dirtext = ''
        print("dirname ", dirname)
        for name in sorted(os.listdir(os.path.join('.', dirname))):
            path = os.path.join(dirname, name)
            if os.path.isdir(path): continue
            if not has_compile_file_ending(path): continue
            d = {}
            d['name'] = os.path.basename(path)
            d['path'] = path
            dirtext += '<li class="file-entry"><a href="/view/{path}">{name}</a></li>'.format(**d)

        for name in sorted(os.listdir(os.path.join('.', dirname))):
            path = os.path.join(dirname, name)
            if not os.path.isdir(path): continue
            subdirtext = dir_entry(path)
            #ignore directories with empty listings
            if subdirtext != '':
                dirtext += '<li class="dir-entry">' + os.path.basename(path) + subdirtext + '</li>'

        if dirtext != '':
            dirtext = '<ul class="file-listing">' + dirtext + '</ul>'
        elif toplevel:
            dirtext = '<i> (no documents)</i>'
        return dirtext

    text += "<h3>Directory contents</h3>"
    text += dir_entry('', toplevel=True)

    text += '</body></html>'

    return text

def needs_update(name, fmt = 'std'):
    out_filename = get_out_filename(name, fmt)
    in_filename = get_in_filename(name)
    if not os.path.exists(in_filename): return False
    if not os.path.exists(out_filename): return True
    return os.path.getmtime(out_filename) < os.path.getmtime(in_filename)

def newer_input_exists(name, time):
    """Returns true iff input file 'name' exists and is newer than 'time'"""
    in_filename = get_in_filename(name)
    if not os.path.exists(in_filename): return False
    return time < os.path.getmtime(in_filename)

def compile_document(name, fmt):
    out_filename = get_out_filename(name, fmt)
    in_filename = get_in_filename(name)
    if needs_update(name, fmt):
        #file is not cached, recompile
        #create directory if needed
        out_filename_dir = os.path.dirname(out_filename)
        if not os.path.exists(out_filename_dir):
            os.makedirs(out_filename_dir)

        #combine action based on format
        action = ['pandoc']

        if fmt == 'std':
            action += ['-H', headerfile, '-B', topmenufile,]

        if fmt == 'export':
            action += ['-H', headerfile_export,]

        if fmt == 'std' or fmt == 'export':
            action += ['-B', beforefile, '-A', afterfile,]
            action += ['--toc']

        if fmt != 'inline':
            action += ['-s']

        # compile
        #print(action)
        # create json in intermediate step
        json_encoding_process = subprocess.Popen(action + ['-t', 'json', in_filename], stdout=subprocess.PIPE)
        json_text, _ = json_encoding_process.communicate()
        json_text = json_text.decode('utf-8')

        # process json to extract embedded dot diagrams and others
        json_text, math_option = process_document_json(json_text, alternative_title=os.path.basename(name))

        # render to HTML
        json_decoding_process = subprocess.Popen(action + math_option + ['-f', 'json', '-o', out_filename], stdin=subprocess.PIPE)
        json_decoding_process.communicate(json_text.encode('utf-8'))

def process_document_json(json_text, alternative_title):
    math_option = ['--mathjax']
    changed = False

    doc = json.loads(json_text)

    # TODO descent recursively into json doc

    for block in doc["blocks"]:
        if block["t"] == "CodeBlock":
            if "dot" in block["c"][0][1]:
                extract_embedding(block, "dot")
                changed = True
            elif "plantuml" in block["c"][0][1]:
                extract_embedding(block, "plantuml")
                changed = True

    # Add title if missing
    if "title" not in doc["meta"] and "pagetitle" not in doc["meta"]:
        doc["meta"]["pagetitle"] = {'t': 'MetaInlines', 'c': [{'t': 'Str', 'c': alternative_title}]}
        changed = True

    # Allow user to select math option using metadata
    if "panserver_math" in doc["meta"]:
        meta_math = doc["meta"]["panserver_math"]["c"][0]["c"]
        print("math option ", meta_math)
        if meta_math == "mathml":
            math_option = ['--mathml']
        elif meta_math == "mathjax":
            math_option = ['--mathjax']
        elif meta_math == "none":
            math_option = []

    if changed:
        json_text = json.dumps(doc)
    return json_text, math_option

def extract_embedding(block, embedding_type):
    code = block["c"][1]
    md5 = hashlib.md5(code.encode('utf-8')).hexdigest()
    generation_dir = os.path.join(tempdir, "generated")
    error = None
    if not os.path.exists(generation_dir):
        os.makedirs(generation_dir)
    target = os.path.join(generation_dir, "{}.{}.png".format(md5, embedding_type))
    if not os.path.exists(target):
        if embedding_type == "dot":
            process = subprocess.Popen(["dot", "-Tpng"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif embedding_type == "plantuml":
            process = subprocess.Popen(["plantuml", "-pipe"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process_out, process_err = process.communicate(code.encode('utf-8'))
        error_code = process.wait()
        if error_code != 0:
            error = process_err.decode('utf-8')
        else:
            with open(target, "wb") as f:
                f.write(process_out)

    if error is None:
        # Replace embedding in block with image
        block["t"] = "Para"
        block["c"] = [ { "t" : "Image", "c" : [
            ["", [], []],
            [],
            [ "/generated/{}.{}.png".format(md5, embedding_type), "fig:"]
            ]}]
    else:
        # Insert error
        block["c"][0][1] = []
        block["c"][1] = error

def create_header(autorefresh):
    headertext = ""
    headertext += """{}<style type="text/css">{}</style>""".format(meta_no_mobilescale, style_basic + style_document_add)
    headertext += markdown_css_link

    if autorefresh:
        headertext += """
    <script>
    window.setInterval(function() {
        var xhr = new XMLHttpRequest();
        var href = window.location.href;
        var re = /view\/(.+?)$/;
        var name = re.exec(href)[1];
        xhr.open('GET', '/refresh/' + name + "?time=" + Math.ceil(window.performance.timing.connectStart / 1000));
        xhr.onload = function() {
            if (xhr.status === 200) {
                if(xhr.responseText == 'True') {
                    window.location.reload();
                }
            }
            else {
                //alert('Request failed! ' + xhr.status);
            }
        };
        xhr.send();
    }, 750);
    </script>
"""

    with open(headerfile, 'w') as f:
        f.write(headertext)

def create_header_export():
    text = """{}<style type="text/css">{}</style>""".format(meta_no_mobilescale, style_basic)
    text += markdown_css_link

    with open(headerfile_export, 'w') as f:
        f.write(text)

def create_topmenufile():
    text = """
    <span class="topmenu">Panserver: <a href="/">Index</a>
    <span style="text-decoration: underline; cursor: pointer" onclick="(tocElement = document.getElementById('TOC')).style.display = (tocElement.style.display != 'block') ? 'block' : 'none';">TOC</span>
    Format:
    <a href="?fmt=export">Export</a>
    <a href="?fmt=simple">Simple</a>
    <a href="?fmt=inline">Inline</a>
    </span>
    """
    with open(topmenufile, 'w') as f:
        f.write(text)

def create_beforefile():
    text = """
    <span class="markdown-body">
    """
    with open(beforefile, 'w') as f:
        f.write(text)

def create_afterfile():
    with open(afterfile, 'w') as f:
        f.write("</span>")

#global vars
file_endings = [".md", ".markdown", ".rst"]
tempdir = tempfile.mkdtemp()
outdir = os.path.join(tempdir, "out")
indir = os.path.abspath('.')

headerfile = os.path.join(tempdir, "header.html")
headerfile_export = os.path.join(tempdir, "header.export.html")
beforefile = os.path.join(tempdir, "before.html")
topmenufile = os.path.join(tempdir, "topmenu.html")
afterfile = os.path.join(tempdir, "after.html")

if not os.path.exists(outdir):
    os.makedirs(outdir)

meta_no_mobilescale = """<meta name="viewport" content="width=device-width, initial-scale=1.0">"""


style_basic = """
        body {
            width: 92%; max-width: 40em;  margin: auto;
            font-size: 1.2rem; line-height: 1.5; padding-bottom: 3em;}
        code { font-family: "DejaVu Sans Mono", Consolas, monospace; }
        pre { overflow: auto; }
        math, .LaTeX { font-size: 1.1em; }
        div.figure .caption {  padding: 0em 1em 1em; font-size: 0.8em; }
        ul li { list-style-type: disc; }
        li p { margin: 0.5em 0; }
        #TOC { border: 1px solid lightgray; padding: 0.5em; margin-bottom: 1em;}
        #TOC li { list-style: circle; }
        @media (min-width: 102em) {
            body { position: relative; }
            #TOC { display: block; position: absolute; left: -50%; top: 5em; max-width: 46%; width: 45%; }
        }
"""

style_document_add = """
        @media (max-width: 101em) {
            #TOC { display: none; }
        }
        .topmenu { font-size: 1em; color: lightgrey; }
        .topmenu a { color: lightgrey; }
"""
style_index = """
        ul.file-listing a { text-decoration: none; }
        ul.file-listing ul.file-listing { padding-left: 1.5em; }
        ul li.dir-entry {
            list-style-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAApElEQVQ4je3UsQqBYRTG8Z9SMpjsrsAdYMI1WNyDhdnKriiD1U3YXML3SWE3uAgDX+lF8iqlPPX01qnn/55OncMvqYMUSeA1KjHAFKUH9S7GMcDkSb2Jk/vOQ2/QhzKq2F/fd52/ftzCBKZYYRnhA2ohcIb6m+PJdJv9A//AT4GND4BZtp0BBxgiFwG8zY7QgyIWLsv96gCE3uKIHeYoRDT1ZZ0BsR1JIXdX8A8AAAAASUVORK5CYII=');
        }
        ul li.file-entry{
            list-style-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAA00lEQVQ4jcXUQUqCURSG4Qc0bKaUiKsIhEbazMBhOHILES3EUYIGtpBwlDODhhFCTqQdtIYGf5H+eOVeFP4P3ul7L4fzHbZziQme9jDEqYhU8IkervbwjecYaRPziIeXuIuRNvESKRQjjRV+4f6XN8xQPkQ4wO0Ga9QPEeazKER4gi6uA3T9zy1KeCZb8McAY1RThCkpRtjAh2yJd/EuG0txPzy68BxT4RM2RS1FWEZH+IS1UUoRpuQ1JPw7sDfCDcnTx0rWrJ1pYSTckDwPuNgU/ADJ7ku1B60bXwAAAABJRU5ErkJggg==');
        }
"""

markdown_css_link= """<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/3.0.1/github-markdown.css">"""

if __name__ == '__main__':
    import webbrowser
    import argparse

    parser = argparse.ArgumentParser(description='Run a local markdown compiling server')

    parser.add_argument('-a', action='store_const', const=True)
    parser.add_argument('-p', '--port', type=int, default=8080)
    parser.add_argument('-b', action='store_const', const=True)
    parser.add_argument('-r', action='store_const', const=True)
    parser.add_argument('path', nargs='?')
    config = parser.parse_args()

    create_header(config.a)
    create_header_export()
    create_topmenufile()
    create_beforefile()
    create_afterfile()

    if config.path != None:
        if os.path.isdir(config.path):
            os.chdir(config.path)
            indir = os.path.abspath('.')
        else:
            raise Exception('Unknown path argument')

    if config.b:
        webbrowser.get().open('http://localhost:{}/'.format(config.port))

    host = 'localhost'
    if config.r:
        host = ''

    bottle.run(host=host, port=config.port)
    shutil.rmtree(outdir)

