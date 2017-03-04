#!/usr/bin/env python2
from collections import defaultdict
from datetime import date, datetime
from email.Utils import formatdate
import frontmatter
import jinja2
import markdown
import os
import sys
import time
import yaml

@jinja2.contextfilter
def _render(context, data):
    return env.from_string(data['source']).render(**context)

def datekey(entry):
    d = entry.get('date', date.min)
    if isinstance(d, date):
        d = datetime.combine(d, datetime.min.time())
    return d

def strip_path(base, path):
    return path.replace(base, '', 1).lstrip(os.sep)

def gen(base, out):
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, loader=jinja2.FileSystemLoader(base))
    env.filters['render'] = _render
    env.filters['markdown'] = lambda x: markdown.markdown(x.decode('utf-8', 'replace'))
    env.filters['date'] = lambda x: x.strftime('%Y-%m-%d')
    env.filters['rfc822'] = lambda x: formatdate(time.mktime(x.timetuple()))
    env.filters['datesort'] = lambda x: sorted(x, key=lambda k: datekey(k))

    tree = defaultdict(list)
    for root, dirs, files in os.walk(base):
        root = strip_path(base, root)
        for name in files:
            if name.endswith('.j2'):
                path = os.path.join(base, root, name)
                post = frontmatter.load(path)
                data = {'name': name.rsplit('.', 1)[0], 'src': path, 'source': post.content}
                data.update(post)
                data['url'] = data.get('url', data['name'])
                data['dst'] = os.path.join(out, os.path.dirname(strip_path(base, path)), data['url'])
                tree[root].append(data)

    for template in (t for ts in tree.values() for t in ts):
        source, render = map(template.get, ('source', 'render'), (None, ''))
        if source is not None:
            if render:
                source = open(os.path.join(base, render), 'r').read()
            ctx = {cat: templates for cat, templates in tree.items() if cat}
            ctx.update(tree=tree, **template)
            data = env.from_string(source).render(**ctx)
            dstdir = os.path.dirname(template['dst'])
            if not os.path.exists(dstdir):
                os.makedirs(dstdir)
            ext = template.get('ext', os.path.splitext(render)[1] if not '.' in name else '')
            with open(template['dst'] + ext, 'w') as o:
                o.write(data.encode('utf-8'))

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print('Usage: gen.py <src> <out>')
        sys.exit(1)
    gen(*sys.argv[1:])
