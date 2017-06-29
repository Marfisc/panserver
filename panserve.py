from bottle import route
import bottle
import webbrowser
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

@route('/')
def route_index():
    return "<h1>PanServe</h1><h2>Serving markdown since yesterday</h2>"

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
        subprocess.call(['pandoc', '-H', headerfile, '-s', '-m', in_filename, '-o', out_filename])

def create_header(autorefresh):
    headertext = """
    <style>
    body { width: 90%;  margin: auto; font-size: 1.1em; }
    .LaTeX { font-size: 1.2em; }
    div.figure .caption {  padding: 0em 1em 1em; font-size: 0.8em; }
    </style>
"""
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
    import argparse

    parser = argparse.ArgumentParser(description='Run a local markdown compiling server')

    parser.add_argument('-a', action='store_const', const=True)
    parser.add_argument('-p', '--port', type=int, default=8080)
    parser.add_argument('file', nargs='?')
    config = parser.parse_args()

    create_header(config.a)

    if config.file != None:
        f = config.file
        if f.endswith('.md'):
            f = f[:-3]

        webbrowser.get().open('http://localhost:{}/view/{}'.format(config.port, config.file))

    bottle.run(host='localhost', port=config.port)
    shutil.rmtree(outdir)
