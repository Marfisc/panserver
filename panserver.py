#!/usr/bin/env python3

from bottle import route
import bottle
import tempfile
import os
import shutil
import subprocess
import json
import hashlib

class FileProvider:

    def __init__(self, indir):
        self.file_endings = ['.md', '.rst']
        self.indir = indir

    def get_in_filename(self, name):
        f = os.path.join(self.indir, self.get_in_filename_rel(name))
        if not os.path.abspath(f).startswith(os.path.abspath(self.indir)):
            raise Exception('Path in problem', os.path.abspath(f), os.path.abspath(self.indir))
        for file_ending in [""] + self.file_endings:
            if os.path.exists(f + file_ending):
                return f + file_ending
        return f

    def get_in_filename_rel(self, name):
        return name

    def is_not_static(self, name):
        f = self.get_in_filename(name)
        for file_ending in self.file_endings:
            if f.endswith(file_ending):
                return True
        return False

    def get_mtime(self, name):
        f = self.get_in_filename(name)
        if not os.path.exists(f):
            return 0
        else:
            return os.path.getmtime(f)

class DocumentCompiler:

    def __init__(self, *, embedding_processor = None, autorefresh = False, export = False, basic_style = False, inline = False, toc = True):
        self.embedding_processor = embedding_processor
        self.autorefresh = autorefresh
        self.export = export
        self.basic_style = basic_style
        self.inline = inline
        self.toc = toc

        self.tempdir = tempfile.mkdtemp()
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)
        self.outdir = os.path.join(self.tempdir, "out")
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)

        self.headerfile = os.path.join(self.tempdir, "headerfile.html")
        self.beforefile = os.path.join(self.tempdir, "beforefile.html")
        self.afterfile = os.path.join(self.tempdir, "afterfile.html")

        self.create_headerfile()
        self.create_beforefile()
        self.create_afterfile()

    def create_headerfile(self):
        text = ""
        text += meta_no_mobilescale
        if not self.basic_style:
            if not self.export:
                text += """<style type="text/css">{}</style>""".format(style_basic + style_document_add)
            else:
                text = """<style type="text/css">{}</style>""".format(style_basic)
            text += markdown_css_link

        if self.autorefresh:
            text += """
        <script>
        window.setInterval(function() {
            if (document.visibilityState === 'hidden') {
                return;
            }
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

        with open(self.headerfile, 'w') as f:
            f.write(text)

    def create_beforefile(self):
        text = ""
        if not self.export:
            text += """
            <span class="topmenu">Panserver: <a href="/">Index</a>
            <span style="text-decoration: underline; cursor: pointer" onclick="(tocElement = document.getElementById('TOC')).style.display = (tocElement.style.display != 'block') ? 'block' : 'none';">TOC</span>
            Format:
            <a href="?fmt=export">Export</a>
            <a href="?fmt=simple">Simple</a>
            <a href="?fmt=inline">Inline</a>
            </span>
            """

        if not self.basic_style:
            text += """
            <span class="markdown-body">
            """
        with open(self.beforefile, 'w') as f:
                f.write(text)

    def create_afterfile(self):
        text = ""
        if not self.basic_style:
            text += "</span>"
        with open(self.afterfile, 'w') as f:
            f.write(text)

    def get_out_filename(self, name):
        f =  os.path.join(self.outdir, self.get_out_filename_rel(name))
        if not os.path.abspath(f).startswith(os.path.abspath(self.outdir)):
            raise Exception('Path out problem', os.path.abspath(f), os.path.abspath(self.outdir))
        return f

    def get_out_filename_rel(self, name):
        return name + ".html"

    def compile_document(self, name, file_provider : FileProvider):
        out_filename = self.get_out_filename(name)

        # Skip if compiled file exists
        if os.path.exists(out_filename) and os.path.getmtime(out_filename) >= file_provider.get_mtime(name):
            return

        #create directory if needed
        out_filename_dir = os.path.dirname(out_filename)
        if not os.path.exists(out_filename_dir):
            os.makedirs(out_filename_dir)

        #combine action based on format
        action = ['pandoc']

        if not self.inline:
            action += ['-s']
            action += ['-H', self.headerfile]
            action += ['-B', self.beforefile, '-A', self.afterfile]

            if self.toc:
                action += ['--toc']

        # compile
        #print(action)
        # create json in intermediate step
        json_encoding_process = subprocess.Popen(action + ['-t', 'json', file_provider.get_in_filename(name)], stdout=subprocess.PIPE)
        json_text, _ = json_encoding_process.communicate()
        json_text = json_text.decode('utf-8')

        # process json to extract embedded dot diagrams and others
        json_text, math_option = self.process_document_json(json_text, alternative_title=os.path.basename(name))

        # render to HTML
        json_decoding_process = subprocess.Popen(action + math_option + ['-f', 'json', '-o', out_filename], stdin=subprocess.PIPE)
        json_decoding_process.communicate(json_text.encode('utf-8'))

    def process_document_json(self, json_text, alternative_title):
        math_option = ['--mathjax=https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-AMS-MML_HTMLorMML']
        changed = False

        doc = json.loads(json_text)

        # TODO descent recursively into json doc

        if self.embedding_processor != None:
            for block in doc["blocks"]:
                if block["t"] == "CodeBlock":
                    can_process = False
                    for fmt in block["c"][0][1]:
                        if self.embedding_processor.is_known_format(fmt):
                            can_process = True
                            break
                    if can_process:
                        self.embedding_processor.process(block, fmt)
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
                math_option = ['--mathjax=https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-AMS-MML_HTMLorMML']
            elif meta_math == "none":
                math_option = []

        if changed:
            json_text = json.dumps(doc)
        return json_text, math_option


class EmbeddingProcessor:

    def __init__(self, programs):
        self.tempdir = tempfile.mkdtemp()
        self.programs = programs
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)

    def is_known_format(self, fmt):
        return fmt in self.programs

    def process(self, block, fmt):
        if not self.is_known_format(fmt):
            return

        code = block["c"][1]
        md5 = hashlib.md5(code.encode('utf-8')).hexdigest()
        error = None
        target = os.path.join(self.tempdir, "{}.{}.png".format(md5, fmt))

        if not os.path.exists(target):
            process = subprocess.Popen(self.programs[fmt], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
                [ "/generated/{}.{}.png".format(md5, fmt), "fig:"]
                ]}]
        else:
            # Insert error
            block["c"][0][1] = []
            block["c"][1] = error

### Routes

@route('/view/<name:path>')
def route_view(name):
    if file_provider.is_not_static(name):
        print("not static")
        fmt = bottle.request.query.fmt or "std"
        if not fmt in document_compilers: return 'Unknown format'
        compiler = document_compilers[fmt]
        compiler.compile_document(name, file_provider)
        return bottle.static_file(compiler.get_out_filename_rel(name), compiler.outdir)

    else:
        return bottle.static_file(file_provider.get_in_filename_rel(name), file_provider.indir)

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
        raise Exception("Missing time parameter in refresh page")

    if result:
        return "True"
    else:
        return "False"

@route('/generated/<name:path>')
def route_generated(name):
    return bottle.static_file(name, embedding_processor.tempdir)

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
        if dirname == '.git':
            return ''
        dirtext = ''
        for name in sorted(os.listdir(os.path.join('.', dirname))):
            path = os.path.join(dirname, name)
            if os.path.isdir(path): continue
            if not file_provider.is_not_static(os.path.basename(path)): continue
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


def newer_input_exists(name, time):
    """Returns true iff input file 'name' exists and is newer than 'time'"""
    return time < file_provider.get_mtime(name)


### Global vars (used only in the routes and main)

file_provider : FileProvider = None
doument_compilers = {}
embedding_processor = EmbeddingProcessor({"dot" : ["dot", "-Tpng"], "plantuml" : ["plantuml", "-pipe"]})

### Text constants

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
        #TOC > ul { margin-bottom: 0px }
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

### Main

def main():
    import webbrowser
    import argparse

    parser = argparse.ArgumentParser(description='Run a local markdown compiling server')

    parser.add_argument('-a', action='store_const', const=True)
    parser.add_argument('-p', '--port', type=int, default=8080)
    parser.add_argument('-b', action='store_const', const=True)
    parser.add_argument('-r', action='store_const', const=True)
    parser.add_argument('path', nargs='?')
    config = parser.parse_args()

    global document_compilers
    document_compilers = {
        "std" : DocumentCompiler(autorefresh = config.a, embedding_processor=embedding_processor),
        "export" : DocumentCompiler(export = True, embedding_processor=embedding_processor),
        "simple" : DocumentCompiler(export = True, basic_style = True, toc = False, embedding_processor=embedding_processor),
        "inline" : DocumentCompiler(inline = True, embedding_processor=embedding_processor)
    }

    if config.path != None:
        if os.path.isdir(config.path):
            os.chdir(config.path)
        else:
            raise Exception('Unknown path argument')
    global file_provider
    file_provider = FileProvider(os.path.abspath('.'))

    if config.b:
        webbrowser.get().open('http://localhost:{}/'.format(config.port))

    host = 'localhost'
    if config.r:
        host = ''

    bottle.run(host=host, port=config.port)

    shutil.rmtree(embedding_processor.tempdir)
    for compiler in doument_compilers.values():
        shutil.rmtree(compiler.tempdir)

if __name__ == '__main__':
    main()

