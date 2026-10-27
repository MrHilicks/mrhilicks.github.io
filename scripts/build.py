#!/usr/bin/env python3
"""Сборка двуязычного статического сайта. Только стандартная библиотека Python."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from string import Template
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_site'
LANGS = ('ru', 'en')
ARROW = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
DIAGONAL = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
LOGO = '<svg viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="m20 5 15 9-15 9-15-9 15-9Z"/><path d="m5 21 15 9 15-9M5 28l15 9 15-9"/></svg>'
ICONS = {
 'map':'<path d="m4 7 8-3 8 3 8-3v22l-8 3-8-3-8 3V7Zm8-3v22M20 7v22"/>',
 'terrain':'<path d="m2 26 9-15 6 8 5-13 9 20H2Zm9-15 3 12m8-17 2 15"/>',
 'volume':'<path d="m16 3 13 7v14l-13 7-13-7V10l13-7Zm0 14L3 10m13 7 13-7M16 17v14M9 6l13 8"/>',
 'vision':'<path d="M4 12V4h8M22 4h8v8M30 22v8h-8M12 30H4v-8M7 17s4-6 10-6 10 6 10 6-4 6-10 6S7 17 7 17Z"/><circle cx="17" cy="17" r="3"/>',
 'code':'<path d="m12 8-8 9 8 9M22 8l8 9-8 9M20 4l-6 26"/>',
 'report':'<path d="M7 3h14l6 6v21H7V3Zm14 0v7h6M12 16h10M12 21h10M12 26h6"/>'
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def breaks(value: str) -> str:
    return '<br>'.join(esc(line) for line in value.split('\n'))


def load_json(name: str) -> dict:
    try:
        return json.loads((ROOT / 'content' / name).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'Cannot read content/{name}: {exc}') from exc


def page_path(lang: str, slug: str | None = None) -> str:
    prefix = '' if lang == 'ru' else 'en/'
    return prefix + (f'projects/{slug}/' if slug else '')


def render(template: str, **values: str) -> str:
    source = (ROOT / 'templates' / template).read_text(encoding='utf-8')
    try:
        return Template(source).substitute(values)
    except KeyError as exc:
        raise ValueError(f'Missing template value {exc} in {template}') from exc


def tags(items: list[str]) -> str:
    return '<div class="tags">' + ''.join(f'<span>{esc(t)}</span>' for t in items) + '</div>'


def button(href: str, label: str, variant: str = 'primary', extra: str = '') -> str:
    return f'<a class="button button--{variant}" href="{esc(href)}" {extra}>{esc(label)}{ARROW}</a>'


class Page:
    def __init__(self, config: dict, text: dict, slug: str | None = None, not_found: bool = False):
        self.config, self.t, self.slug = config, text, slug
        self.lang = text['lang']
        self.display_name = config.get('names', {}).get(self.lang, config['name'])
        self.media = load_json('media.json')
        self.path = page_path(self.lang, slug)
        self.not_found = not_found
        self.base = '../' * self.path.count('/') or './'
        if not_found:
            # Страница 404 может открываться на любой глубине URL.
            self.base = urlparse(config['site_url']).path.rstrip('/') + '/'

    def link(self, target: str) -> str:
        return self.base + target

    def home(self, anchor: str = '') -> str:
        return self.link(page_path(self.lang)) + (f'#{anchor}' if anchor else '')

    def image(self, name: str, alt: str, cls: str = '', eager: bool = False, width: int = 1200, height: int = 720, sizes: str = '(max-width: 760px) 100vw, 50vw') -> str:
        info = self.media.get(name, {})
        width, height = info.get('width', width), info.get('height', height)
        attr = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
        variants = info.get('variants', [])
        responsive = ''
        if variants:
            candidates = [f'{self.link("assets/images/" + v["file"])} {v["width"]}w' for v in variants]
            candidates.append(f'{self.link("assets/images/" + name)} {width}w')
            responsive = f' srcset="{esc(", ".join(candidates))}" sizes="{esc(sizes)}"'
        return f'<img class="{esc(cls)}" data-media-name="{esc(name)}" src="{esc(self.link("assets/images/" + name))}" alt="{esc(alt)}" width="{width}" height="{height}" decoding="async" {attr}{responsive}>'

    def header(self) -> str:
        t = self.t
        nav = ''.join(f'<a href="{esc(self.home(anchor))}">{esc(label)}</a>' for anchor, label in t['nav'])
        language_parts = []
        for lang in LANGS:
            current = ' aria-current="page"' if lang == self.lang else ''
            language_parts.append(
                f'<a href="{esc(self.link(page_path(lang, self.slug)))}" lang="{lang}" '
                f'hreflang="{lang}" data-language-link{current}>{lang.upper()}</a>'
            )
        language = ''.join(language_parts)
        return render('header.html', logo=LOGO, home=esc(self.home()), name=esc(self.display_name), nav=nav,
                      nav_label=esc(t['nav_label']), language_label=esc(t['language_label']), language=language,
                      contact_url=esc(self.home('contact')), contact=esc(t['contact_nav']), arrow=DIAGONAL, brand_line=esc(t['brand_line']),
                      menu=esc(t['menu']))

    def footer(self) -> str:
        t = self.t
        links=[]
        for key, label in [('github_url','GitHub'), ('telegram_url','Telegram'), ('linkedin_url','LinkedIn')]:
            if self.config.get(key):
                links.append(f'<a href="{esc(self.config[key])}" target="_blank" rel="noopener noreferrer">{label}{DIAGONAL}</a>')
        return render('footer.html', logo=LOGO, name=esc(self.display_name), home=esc(self.home()),
                      line=esc(t['footer_line']), social=''.join(links), top=esc(t['footer_top']),
                      copyright=esc(self.config['copyright_year']), demo=esc(t['footer_demo']))

    def brief(self) -> str:
        t=self.t
        mail = f'<a class="button button--ghost" id="brief-email" href="mailto:{esc(self.config["email"])}" hidden>{esc(t["brief_mail"])}{ARROW}</a>' if self.config['email'] else ''
        keys=['brief_title','brief_intro','brief_task','brief_task_placeholder','brief_data','brief_data_placeholder',
              'brief_output','brief_output_placeholder','brief_copy','brief_privacy','brief_result','close']
        values={k:esc(t[k]) for k in keys}
        return render('brief.html', **values, mail=mail, arrow=ARROW)

    def contact(self) -> str:
        t = self.t
        email = self.config['email']
        email_button = button('mailto:' + email, t['contact_email'], 'light') if email else ''
        telegram = self.config.get('telegram_url', '')
        telegram_button = button(telegram, t['contact_telegram'], 'outline', 'target="_blank" rel="noopener noreferrer"') if telegram else ''
        details = []
        if email:
            details.append(f'<a href="mailto:{esc(email)}">{esc(email)}</a>')
        if telegram:
            handle = urlparse(telegram).path.strip('/').split('/')[0]
            details.append(f'<a href="{esc(telegram)}" target="_blank" rel="noopener noreferrer">Telegram · @{esc(handle)}</a>')
        return render('contact.html', eyebrow=esc(t['contact_eyebrow']), title=breaks(t['contact_title']),
                      text=esc(t['contact_text']), cta=esc(t['contact_cta']), arrow=ARROW,
                      email=email_button, telegram=telegram_button, details=''.join(details),
                      note=esc(t['contact_note'] if email else t['contact_missing']))

    def viewer(self) -> str:
        t = self.t
        return render('viewer.html', title=esc(t['gallery_title']), close=esc(t['close']),
                      previous=esc(t['gallery_previous']), next=esc(t['gallery_next']),
                      zoom=esc(t['gallery_zoom']), original=esc(t['gallery_original']),
                      count_word=esc(t['gallery_count_word']))

    def comparison(self, project: dict) -> str:
        data = project.get('comparison')
        if not data:
            return ''
        t = self.t
        return render('comparison.html', title=esc(t['comparison_title']), intro=esc(t['comparison_intro']),
                      before_label=esc(t['comparison_before']), after_label=esc(t['comparison_after']),
                      control=esc(t['comparison_control']), note=esc(t['comparison_note']),
                      before=self.image(data['before'], t['comparison_before'], sizes='(max-width: 760px) 100vw, 600px'),
                      after=self.image(data['after'], t['comparison_after'], sizes='(max-width: 760px) 100vw, 600px'))

    def finish(self, body: str, title: str, description: str, image: str = 'construction-card.webp', indexable: bool = True) -> str:
        t=self.t
        site_url=self.config['site_url'].rstrip('/')
        canonical=site_url + '/' + ('404.html' if self.not_found else self.path)
        alternates=''.join(f'<link rel="alternate" hreflang="{lang}" href="{esc(site_url+"/"+page_path(lang,self.slug))}">' for lang in LANGS)
        if self.not_found:
            alternates=''
        else:
            alternates+=f'<link rel="alternate" hreflang="x-default" href="{esc(site_url+"/"+page_path("ru",self.slug))}">'
        robots='index, follow' if self.config['indexable'] and indexable and not self.not_found else 'noindex, follow'
        fonts=''
        if self.config.get('use_google_fonts'):
            fonts='''<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&amp;family=Manrope:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">'''
        client={k:t[k] for k in ('brief_task','brief_data','brief_output','brief_ready','brief_copied','brief_fallback','brief_subject','brief_required')}
        client['email']=self.config['email']
        # Экранируем <, чтобы даже пользовательский текст не закрыл JSON script.
        client_json=json.dumps(client,ensure_ascii=False).replace('<','\\u003c')
        structured=json.dumps({'@context':'https://schema.org','@type':'Person','name':self.display_name,
                               'url':site_url+'/', 'knowsLanguage':['en','ru'], 'jobTitle':'Machine Learning & Data Analysis Specialist', 'email':self.config['email'], 'sameAs':[self.config[k] for k in ('github_url','telegram_url','linkedin_url') if self.config.get(k)], 'knowsAbout':['Data Science','Machine Learning','Computer Vision','Aerial imagery analysis']},ensure_ascii=False).replace('<','\\u003c')
        return render('layout.html', lang=self.lang, title=esc(title), description=esc(description),
                      canonical=esc(canonical), alternates=alternates, robots=robots, fonts=fonts,
                      og_image=esc(site_url+'/assets/images/'+image), locale=esc(t['locale']),
                      assets=esc(self.link('assets/')), skip=esc(t['skip']),
                      header=self.header(), body=body, footer=self.footer(), brief=self.brief(),
                      client_json=client_json, structured=structured, viewer=self.viewer() if self.slug else '', version=esc(self.config.get('version', '1.1.0')),
                      page_class='page-case' if self.slug else 'page-home')

    def card(self, project: dict) -> str:
        t=self.t; planned=project['status']=='planned'
        badge=t['planned_badge'] if planned else t['demo_badge']
        href=self.link(page_path(self.lang,project['slug']))
        metric='' if planned else f'<div class="project-metric"><strong>{esc(project["metric"])}</strong><span>{esc(project["metric_label"])}</span></div>'
        label=t['planned_link'] if planned else t['case_link']
        return render('project-card.html', href=esc(href), modifier='project-card--planned' if planned else '',
                      image=self.image(project['image'],project['image_alt']), number=esc(project['number']),
                      category=esc(project['category']), badge=esc(badge), title=breaks(project['title']),
                      summary=esc(project['summary']), tags=tags(project['tags']), metric=metric,
                      label=esc(label), arrow=DIAGONAL)

    def home_body(self) -> str:
        t=self.t
        cards=''.join(self.card(p) for p in t['projects'])
        services=''.join(
            f'<article class="service-row"><span class="service-number">0{i+1}</span>'
            f'<div class="service-icon"><svg viewBox="0 0 34 34" fill="none" aria-hidden="true">{ICONS[p["icon"]]}</svg></div>'
            f'<h3>{esc(p["title"])}</h3><div class="service-description"><p>{esc(p["text"])}</p>{tags(p["tags"])}</div></article>'
            for i,p in enumerate(t['services']))
        steps=''.join(f'<li><span class="step-number">0{i+1}</span><h3>{esc(title)}</h3><p>{esc(text)}</p></li>' for i,(title,text) in enumerate(t['steps']))
        report_links=''.join(
            f'<a class="report-link" href="{esc(self.link("assets/reports/"+p["report"]))}" target="_blank" rel="noopener noreferrer">'
            f'<span><strong>{esc(p["full_title"])}</strong><small>{esc(t["pdf_label"])}</small></span>{DIAGONAL}</a>'
            for p in t['projects'] if p.get('report'))
        faqs=''.join(f'<details class="faq-item"><summary>{esc(q)}<span aria-hidden="true">+</span></summary><p>{esc(a)}</p></details>' for q,a in t['faqs'])
        params={k:esc(t[k]) for k in ('hero_eyebrow','hero_title','hero_accent','hero_text','hero_note',
                'hero_primary','hero_panel_label','ortho','surface','hero_caption','hero_disclaimer','hero_images','hero_crs',
                'strip_label','work_eyebrow','work_title','work_intro','expertise_eyebrow','expertise_title',
                'expertise_intro','process_eyebrow','process_intro','process_note',
                'deliver_eyebrow','deliver_text','report_language','about_eyebrow','about_text','about_text_2',
                'about_note','about_quote','faq_eyebrow','faq_title','experience_value','experience_label')}
        params.update({k:breaks(t[k]) for k in ('process_title','deliver_title','about_title')})
        return render('home.html', **params,
                      primary=button('#work',t['hero_primary']), secondary=button('#contact',t['hero_secondary'],'outline'),
                      hero_image=self.image('construction-cutout.webp',t['hero_image_alt'],'map-photo',True,1200,1086),
                      hero_surface=self.image('construction-dsm.webp',t['hero_surface_alt'],'map-surface',False,1685,1506),
                      strip=''.join(f'<span>{esc(item)}</span>' for item in t['strip_items']),
                      cards=cards, services=services, steps=steps, report_links=report_links,
                      report_construction=self.image('report-construction.webp',t['projects'][0]['full_title'],'report-cover report-cover--landscape',False,758,536),
                      report_road=self.image('report-road.webp',t['projects'][1]['full_title'],'report-cover report-cover--portrait',False,714,1010),
                      about_tags=tags(t['about_tags']), name=esc(self.display_name),
                      faqs=faqs, contact=self.contact(), logo=LOGO, arrow=DIAGONAL)

    def case_body(self, project: dict) -> str:
        t=self.t;planned=project['status']=='planned'
        facts='' if planned else '<div class="case-facts">'+''.join(f'<div><strong>{esc(v)}</strong><span>{esc(k)}</span></div>' for v,k in project['facts'])+'</div>'
        report=button(self.link('assets/reports/'+project['report']),t['download']+' · PDF','primary','target="_blank" rel="noopener noreferrer"') if project.get('report') else ''
        gallery = ''
        if project['gallery']:
            figures = []
            for i, g in enumerate(project['gallery'], 1):
                modifier = ' case-figure--wide' if g.get('wide') else ''
                sizes = '(max-width: 760px) 100vw, 1280px' if g.get('wide') else '(max-width: 760px) 100vw, 620px'
                image = self.image(g['file'], g['alt'], sizes=sizes)
                href = self.link('assets/images/' + g['file'])
                figures.append(f'<figure class="case-figure{modifier}"><a class="gallery-open" href="{esc(href)}" target="_blank" rel="noopener noreferrer" data-gallery data-caption="{esc(g["caption"])}" aria-label="{esc(t["gallery_open"])}: {esc(g["alt"])}">{image}<span class="gallery-expand" aria-hidden="true">{DIAGONAL}</span></a><figcaption><span class="gallery-number">{i:02d}</span><span>{esc(g["caption"])}</span></figcaption></figure>')
            gallery = f'<section class="case-gallery container" id="gallery" aria-labelledby="gallery-title"><p class="eyebrow">{esc(t["case_gallery"])}</p><h2 id="gallery-title">{esc(t["gallery_heading"])}</h2><p class="gallery-intro">{esc(t["gallery_intro"])}</p><div class="gallery-grid">{"".join(figures)}</div></section>'
        source_links = []
        for key, label in [('source_url', 'source_link_label'), ('license_url', 'license_link_label')]:
            if project.get(key):
                source_links.append(f'<a href="{esc(project[key])}" target="_blank" rel="noopener noreferrer">{esc(t[label])}{DIAGONAL}</a>')
        gallery_jump = button('#gallery', t['gallery_jump'], 'ghost') if project['gallery'] else ''
        notice=t['case_plan_notice'] if planned else t['case_demo_notice']
        caption=t['case_plan_image'] if planned else t['demo_badge']
        next_project=t['projects'][(t['projects'].index(project)+1)%len(t['projects'])]
        return render('case.html', back_url=esc(self.home('work')), back=esc(t['case_back']),
                      category=esc(project['category']), badge=esc(t['planned_badge'] if planned else t['demo_badge']),
                      title=esc(project['full_title']), summary=esc(project['summary']),
                      hero=self.image(project['image'],project['image_alt'],'case-hero-image',True), caption=esc(caption),
                      facts=facts, notice=esc(notice), objective_label=esc(t['case_objective']), objective=esc(project['objective']),
                      inputs_label=esc(t['case_inputs']), inputs=esc(project['inputs']),
                      method_label=esc(t['case_method']), method=''.join(f'<li>{esc(x)}</li>' for x in project['method']),
                      outputs_label=esc(t['case_plan_output'] if planned else t['case_outputs']),
                      outputs=''.join(f'<li>{esc(x)}</li>' for x in project['outputs']),
                      limits_label=esc(t['case_limits']), limits=esc(project['limits']),
                      source_label=esc(t['case_source']), source=esc(project['source']),
                      report=report, report_note=esc(t['case_report_note'] if report else ''), gallery=gallery, gallery_jump=gallery_jump, comparison=self.comparison(project), source_links=''.join(source_links),
                      next_label=esc(t['case_next']), next_title=esc(next_project['full_title']),
                      next_url=esc(self.link(page_path(self.lang,next_project['slug']))), arrow=ARROW,
                      contact=self.contact())


def validate_content(config: dict, translations: dict[str,dict]) -> None:
    if set(translations['en']) != set(translations['ru']):
        raise ValueError('EN and RU must have the same top-level keys.')
    for key in ('site_url','github_url','telegram_url','linkedin_url'):
        value=config.get(key,'')
        if value and (urlparse(value).scheme!='https' or not urlparse(value).netloc):
            raise ValueError(f'{key} must be an absolute https URL.')
    if config['email'] and not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',config['email']):
        raise ValueError('Invalid email in content/site.json')
    en_slugs=[p['slug'] for p in translations['en']['projects']]
    if len(set(en_slugs))!=len(en_slugs):
        raise ValueError('Project slugs must be unique.')
    for lang,t in translations.items():
        if t['lang']!=lang or [p['slug'] for p in t['projects']]!=en_slugs:
            raise ValueError('Project slugs and order must match between languages.')
        for p in t['projects']:
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p['slug']):
                raise ValueError(f'Invalid project slug: {p["slug"]}')
            if p['status'] not in ('demo','planned'):
                raise ValueError('Project status must be demo or planned.')
            paths=['images/'+p['image']]+['images/'+g['file'] for g in p['gallery']]
            if p.get('report'):paths.append('reports/'+p['report'])
            if p.get('comparison'):paths.extend('images/'+p['comparison'][k] for k in ('before','after'))
            for key in ('source_url','license_url'):
                if p.get(key) and (urlparse(p[key]).scheme != 'https' or not urlparse(p[key]).netloc):
                    raise ValueError(f'Invalid project source URL: {key}')
            for name in paths:
                resolved=(ROOT/'assets'/name).resolve()
                if not resolved.is_relative_to(ROOT/'assets') or not resolved.is_file():
                    raise ValueError(f'Missing or invalid asset: {name}')


def write_page(relative: str, content: str) -> None:
    target=OUT/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix(target.suffix+'.tmp')
    temp.write_text(content,encoding='utf-8')
    temp.replace(target)


def build() -> list[str]:
    config=load_json('site.json')
    translations={lang:load_json(lang+'.json') for lang in LANGS}
    validate_content(config,translations)
    OUT.mkdir(exist_ok=True)
    # Копируем только изменившиеся исходники; исходные файлы пользователя не удаляются.
    for source in (ROOT/'assets').rglob('*'):
        if source.is_file():
            target=OUT/'assets'/source.relative_to(ROOT/'assets')
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() or source.stat().st_mtime_ns!=target.stat().st_mtime_ns or source.stat().st_size!=target.stat().st_size:
                shutil.copy2(source,target)
    produced=[]
    sitemap=[]
    for lang,t in translations.items():
        home=Page(config,t)
        path=page_path(lang)+'index.html'
        write_page(path,home.finish(home.home_body(),t['meta_title'],t['meta_description']))
        produced.append(path)
        sitemap.append(config['site_url'].rstrip('/')+'/'+page_path(lang))
        for p in t['projects']:
            page=Page(config,t,p['slug'])
            path=page_path(lang,p['slug'])+'index.html'
            write_page(path,page.finish(page.case_body(p),p['full_title']+' — '+page.display_name,p['summary'],p['image'],p['status']=='demo'))
            produced.append(path)
            if p['status']=='demo':sitemap.append(config['site_url'].rstrip('/')+'/'+page_path(lang,p['slug']))
    t=translations['ru'];page=Page(config,t,not_found=True)
    error=f'<section class="error-page container"><p class="eyebrow">404 / NOT FOUND</p><h1>{esc(t["404_title"])}</h1><p>{esc(t["404_text"])}</p>{button(page.home(),t["404_cta"])}</section>'
    write_page('404.html',page.finish(error,'404 — '+config['name'],t['404_text'],indexable=False))
    produced.append('404.html')
    for old in OUT.rglob('*.html'):
        if old.relative_to(OUT).as_posix() not in produced:old.unlink()
    urls=''.join(f'<url><loc>{esc(url)}</loc></url>' for url in sitemap) if config['indexable'] else ''
    write_page('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>')
    # Не закрываем обход: поисковику нужно прочитать noindex на черновых страницах.
    robots='User-agent: *\nAllow: /\n'
    if config['indexable']:robots+='Sitemap: '+config['site_url'].rstrip('/')+'/sitemap.xml\n'
    write_page('robots.txt',robots)
    write_page('.nojekyll','')
    return produced


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        pages=build()
    except (OSError,ValueError,KeyError) as exc:
        parser.exit(1,f'Build failed: {exc}\n')
    print(f'Built {len(pages)} HTML pages in {OUT}')
