#!/usr/bin/env python2
from collections import defaultdict
from email.Utils import formatdate
import jinja2
import markdown
import os
import re
import sys
import time
import yaml


env = jinja2.Environment(
    trim_blocks=True,
    lstrip_blocks=True,
)

@jinja2.contextfilter
def render(context, data):
    return env.from_string(data['source']).render(**context)

env.filters['render'] = render
env.filters['markdown'] = markdown.markdown
env.filters['date'] = lambda x: x.strftime('%Y-%m-%d')
env.filters['rfc822'] = lambda x: formatdate(time.mktime(x.timetuple()))
env.filters['datesort'] = lambda x: sorted(x, key=lambda k: k['date'])


frontmatter_re = re.compile(r'^\s*?---(.*?)---\s*?$(.*)', re.MULTILINE | re.DOTALL)

def strip_path(base, path):
    return path.replace(base, '', 1).lstrip(os.sep)

def find(base, ext):
    for root, dirs, files in os.walk(base):
        root = strip_path(base, root)
        for name in files:
            if name.endswith(ext):
                yield base, root, name

def makedirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

class Generator:
    def __init__(self, base, out):
        self.base = os.path.abspath(base)
        self.out = os.path.abspath(out)
        env.loader = jinja2.FileSystemLoader(base)

    def build(self):
        context = {}
        tree = self.build_tree()
        for cat, templates in tree.items():
            if cat:
                context[cat] = templates

        for templates in tree.values():
            for template in templates:
                if template.get('valid'):
                    template = template.copy()
                    render = template.get('render')
                    if render:
                        source = open(os.path.join(self.base, render), 'r').read()
                    else:
                        source = template.get('source', '')
                    ctx = context.copy()
                    ctx.update(template)
                    data = env.from_string(source).render(**ctx)
                    makedirs(os.path.dirname(template['dst']))
                    with open(template['dst'], 'w') as o:
                        o.write(data)

    def parse_template(self, path):
        name = os.path.basename(path).rsplit('.', 1)[0]
        out = os.path.join(self.out, strip_path(self.base, path))
        data = {
            'name': name,
            'src': path,
        }
        with open(path) as f:
            template = f.read()
            frontmatter, template = frontmatter_re.match(template).groups()
            if frontmatter:
                data['valid'] = True
            data.update(yaml.load(frontmatter))
            data['source'] = template.replace('\n', '', 1)

        if not 'url' in data:
            data['url'] = data['name']
        data['dst'] = os.path.join(os.path.dirname(out), data['url']) + '.html'
        return data

    def build_tree(self):
        tree = defaultdict(list)
        for base, root, name in find(self.base, '.j2'):
            path = os.path.join(base, root, name)
            tree[root].append(self.parse_template(path))

        return tree

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 2:
        path = sys.argv[1]
        out = sys.argv[2]
    else:
        path = os.path.dirname(sys.argv[0]) or '.'
        out = os.path.join(path, '../out')

    gen = Generator(path, out)
    gen.build()
