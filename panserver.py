from bottle import route
import bottle
import tempfile
import os
import shutil
import subprocess

outdir = tempfile.mkdtemp()
indir = os.path.abspath('.')

headerfile = os.path.join(outdir, "header.html")

def get_out_filename(name):
    f =  os.path.join(outdir, get_out_filename_rel(name))
    if not os.path.abspath(f).startswith(os.path.abspath(outdir)):
        raise Exception('Path out problem', os.path.abspath(f), os.path.abspath(outdir))
    return f

def get_out_filename_rel(name):
    return "{}.html".format(name)

def get_in_filename(name, hasExtesion=False):
    f = os.path.join(indir, get_in_filename_rel(name, hasExtesion))
    if not os.path.abspath(f).startswith(os.path.abspath(indir)):
        raise Exception('Path in problem', os.path.abspath(f), os.path.abspath(indir))
    return f

def get_in_filename_rel(name, hasExtesion):
    if not hasExtesion:
        return "{}.md".format(name)
    return name

@route('/view/<name:re:(\w|\.|/)+?><end:re:(.md)?>')
def route_view(name, end):
    md_file = get_in_filename(name)
    if end != "" or os.path.exists(md_file):
        compile_md(name)
        return bottle.static_file(get_out_filename_rel(name), outdir)
    else:
        return bottle.static_file(get_in_filename_rel(name, True), indir)

@route('/refresh/<name:re:(\w|\.|/)+>')
def route_refresh(name):
    if needs_update(name):
        return "True"
    return "False"

@route('/static/style.css')
def route_static_css():
    bottle.response.content_type = 'text/css; charset=UTF8'
    return """
body { width: 90%;  margin: auto; font-size: 1.1em; }
.LaTeX { font-size: 1.2em; }
div.figure .caption {  padding: 0em 1em 1em; font-size: 0.8em; }
ul.file-listing a { text-decoration: none; }
ul li{ list-style-type: disc; }
ul li.dir-entry {
    list-style-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAApElEQVQ4je3UsQqBYRTG8Z9SMpjsrsAdYMI1WNyDhdnKriiD1U3YXML3SWE3uAgDX+lF8iqlPPX01qnn/55OncMvqYMUSeA1KjHAFKUH9S7GMcDkSb2Jk/vOQ2/QhzKq2F/fd52/ftzCBKZYYRnhA2ohcIb6m+PJdJv9A//AT4GND4BZtp0BBxgiFwG8zY7QgyIWLsv96gCE3uKIHeYoRDT1ZZ0BsR1JIXdX8A8AAAAASUVORK5CYII=');
}
ul li.file-entry{
    list-style-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAA00lEQVQ4jcXUQUqCURSG4Qc0bKaUiKsIhEbazMBhOHILES3EUYIGtpBwlDODhhFCTqQdtIYGf5H+eOVeFP4P3ul7L4fzHbZziQme9jDEqYhU8IkervbwjecYaRPziIeXuIuRNvESKRQjjRV+4f6XN8xQPkQ4wO0Ga9QPEeazKER4gi6uA3T9zy1KeCZb8McAY1RThCkpRtjAh2yJd/EuG0txPzy68BxT4RM2RS1FWEZH+IS1UUoRpuQ1JPw7sDfCDcnTx0rWrJ1pYSTckDwPuNgU/ADJ7ku1B60bXwAAAABJRU5ErkJggg==');
}

    """

@route('/')
def route_index():
    import glob

    text = ""

    text += "<html><head>"
    text += '<link rel="stylesheet" type="text/css" href="/static/style.css">'
    text += "</head><body>"
    text += '<h1>Panserver</h1>'
    text += 'Serving Markdown documents rendered using <a href="http://pandoc.org/">pandoc</a>. By <a href="http://marcelfischer.eu/">Marcel Fischer</a>'

    def dir_entry(dirname):
        dirtext = '<ul class="file-listing">'
        for path in sorted(glob.iglob(os.path.join(dirname, '*.md'))):
            if os.path.isdir(path): continue
            d = {}
            d['path'] = path[:-3]
            d['name'] = os.path.basename(path)
            dirtext += '<li class="file-entry"><a href="/view/{path}">{name}</a></li>'.format(**d)

        for path in sorted(glob.iglob(os.path.join(dirname, '*'))):
            if not os.path.isdir(path): continue
            subdirtext = dir_entry(path)
            dirtext += '<li class="dir-entry">' + os.path.basename(path) + subdirtext + '</li>'

        return dirtext + '</ul>'

    text += "<h3>Directory contents</h3>"
    text += dir_entry('')

    text += '</body></html>'

    return text

def needs_update(name):
    out_filename = get_out_filename(name)
    in_filename = get_in_filename(name)
    if not os.path.exists(in_filename): return False
    if not os.path.exists(out_filename): return True
    return os.path.getmtime(out_filename) < os.path.getmtime(in_filename)

def compile_md(name):
    out_filename = get_out_filename(name)
    in_filename = get_in_filename(name)
    if needs_update(name):
        #file is not cached, recompile
        #create directory if needed
        out_filename_dir = os.path.dirname(out_filename)
        if not os.path.exists(out_filename_dir):
            os.makedirs(out_filename_dir)

        #compile
        subprocess.call(['pandoc', '-H', headerfile, '-s', '-m', in_filename, '-o', out_filename])

def create_header(autorefresh):
    headertext = '<link rel="stylesheet" type="text/css" href="/static/style.css"/>'
    if autorefresh:
        headertext += """
    <script>
    window.setInterval(function() {
        var xhr = new XMLHttpRequest();
        var href = window.location.href;
        var re = /view\/(.+?)(.md)?$/;
        var name = re.exec(href)[1];
        xhr.open('GET', '/refresh/' + name);
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

if __name__ == '__main__':
    import webbrowser
    import argparse

    parser = argparse.ArgumentParser(description='Run a local markdown compiling server')

    parser.add_argument('-a', action='store_const', const=True)
    parser.add_argument('-p', '--port', type=int, default=8080)
    parser.add_argument('-b', action='store_const', const=True)
    parser.add_argument('path', nargs='?')
    config = parser.parse_args()

    create_header(config.a)

    if config.path != None:
        if os.path.isdir(config.path):
            os.chdir(config.path)
            indir = os.path.abspath('.')
        else:
            raise Exception('Unknown path argument')

    if config.b:
        webbrowser.get().open('http://localhost:{}/'.format(config.port))

    bottle.run(host='localhost', port=config.port)
    shutil.rmtree(outdir)

