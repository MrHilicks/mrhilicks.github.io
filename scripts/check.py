#!/usr/bin/env python3
"""Проверка готовых HTML: ссылки, якоря, изображения, локализация и JSON."""
from __future__ import annotations
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from build import ROOT, OUT, build

class Document(HTMLParser):
    def __init__(self,path):
        super().__init__(convert_charrefs=True)
        self.path=path;self.ids=set();self.duplicates=[];self.references=[];self.images=[]
        self.h1=0;self.main=0;self.lang=None;self.json_blocks=[];self._json=None
        self.feed(path.read_text(encoding='utf-8'))
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):
            if a['id'] in self.ids:self.duplicates.append(a['id'])
            self.ids.add(a['id'])
        if tag=='html':self.lang=a.get('lang')
        if tag=='h1':self.h1+=1
        if tag=='main':self.main+=1
        if tag=='img':
            self.images.append(a)
            for candidate in a.get('srcset','').split(','):
                if candidate.strip():self.references.append(candidate.strip().split()[0])
        for key in ('href','src'):
            if key in a:self.references.append(a[key])
        if tag=='script' and a.get('type') in ('application/json','application/ld+json'):
            self._json=[]
    def handle_data(self,data):
        if self._json is not None:self._json.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self._json is not None:
            self.json_blocks.append(''.join(self._json));self._json=None

def check():
    errors=[];references=0
    documents={p.resolve():Document(p) for p in OUT.rglob('*.html')}
    basepath=urlparse(json.loads((ROOT/'content/site.json').read_text())['site_url']).path.rstrip('/')
    for path,d in documents.items():
        label=path.relative_to(OUT).as_posix()
        if d.h1!=1:errors.append(f'{label}: expected one h1, got {d.h1}')
        if d.main!=1:errors.append(f'{label}: expected one main')
        if d.lang not in ('en','ru'):errors.append(f'{label}: invalid lang')
        if d.duplicates:errors.append(f'{label}: duplicate IDs {d.duplicates}')
        for image in d.images:
            if 'alt' not in image:errors.append(f'{label}: image without alt')
            if not image.get('width') or not image.get('height'):errors.append(f'{label}: image without dimensions')
        for block in d.json_blocks:
            try:json.loads(block)
            except json.JSONDecodeError:errors.append(f'{label}: invalid embedded JSON')
        for ref in d.references:
            parsed=urlparse(ref)
            if parsed.scheme or parsed.netloc:continue
            references+=1
            name=unquote(parsed.path)
            if not name:target=path
            elif name.startswith('/'):
                if basepath and name.startswith(basepath+'/'):name=name[len(basepath):]
                target=(OUT/name.lstrip('/')).resolve()
            else:target=(path.parent/name).resolve()
            if target.is_dir():target=target/'index.html'
            if not target.is_relative_to(OUT):errors.append(f'{label}: reference outside output: {ref}');continue
            if not target.is_file():errors.append(f'{label}: missing reference: {ref}');continue
            if parsed.fragment and target.suffix=='.html':
                dest=documents.get(target.resolve())
                if dest and unquote(parsed.fragment) not in dest.ids:errors.append(f'{label}: missing anchor: {ref}')
    if errors:
        for error in errors:print('ERROR:',error)
        return 1
    print(f'PASS: {len(documents)} HTML pages; {references} local references; no missing files, broken anchors or duplicate IDs.')
    return 0

if __name__=='__main__':
    build()
    sys.exit(check())
