/* Прогрессивное улучшение: тексты, ссылки, кейсы и PDF работают без JavaScript. */
'use strict';

(() => {
  const nav = document.getElementById('main-nav');
  const toggle = document.querySelector('.menu-toggle');
  if (nav && toggle) {
    const setMenu = (open, restoreFocus = false) => {
      nav.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      if (restoreFocus) toggle.focus();
    };
    toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
    nav.addEventListener('click', (event) => {
      if (event.target.closest('a')) setMenu(false);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') setMenu(false, true);
    });
    document.addEventListener('click', (event) => {
      if (!event.target.closest('.site-header')) setMenu(false);
    });
    window.matchMedia('(min-width: 761px)').addEventListener('change', () => setMenu(false));
    toggle.hidden = false;
    document.documentElement.classList.add('js-nav');
  }

  // Переключение языка ведёт на тот же кейс и сохраняет якорь секции.
  document.querySelectorAll('[data-language-link]').forEach((link) => {
    link.addEventListener('click', () => {
      const target = new URL(link.href, window.location.href);
      target.hash = window.location.hash;
      link.href = target.href;
    });
  });

  const mapControls = document.querySelector('[data-map-controls]');
  if (mapControls) {
    const modes = ['ortho', 'surface'];
    mapControls.querySelectorAll('[data-map]').forEach((button) => {
      button.addEventListener('click', () => {
        const selected = button.dataset.map;
        modes.forEach((mode) => {
          const panel = document.getElementById(`map-${mode}`);
          const control = mapControls.querySelector(`[data-map="${mode}"]`);
          if (panel && control) {
            panel.hidden = mode !== selected;
            control.setAttribute('aria-pressed', String(mode === selected));
          }
        });
      });
    });
    mapControls.hidden = false;
  }

  // Конструктор описания задачи не делает HTTP-запросов и не хранит введённые данные.
  const dialog = document.getElementById('brief-dialog');
  const form = document.getElementById('brief-form');
  const configElement = document.getElementById('site-client-data');
  if (!dialog || !form || !configElement || typeof dialog.showModal !== 'function') return;
  let copy;
  try {
    copy = JSON.parse(configElement.textContent);
  } catch {
    return;
  }
  let returnFocus = null;
  document.querySelectorAll('[data-open-brief]').forEach((button) => {
    button.hidden = false;
    button.addEventListener('click', () => {
      if (dialog.open) return;
      returnFocus = button;
      dialog.showModal();
      document.body.classList.add('modal-open');
    });
  });
  dialog.querySelector('[data-close-brief]')?.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (event) => {
    const rect = dialog.getBoundingClientRect();
    const outside = event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom;
    if (event.target === dialog && outside) dialog.close();
  });
  dialog.addEventListener('close', () => {
    document.body.classList.remove('modal-open');
    returnFocus?.focus({ preventScroll: true });
  });

  const task = document.getElementById('brief-task');
  const result = document.getElementById('brief-result');
  const resultWrap = document.getElementById('brief-result-wrap');
  const status = document.getElementById('brief-status');
  const mail = document.getElementById('brief-email');
  let version = 0;
  form.addEventListener('input', () => {
    version += 1;
    task.setCustomValidity('');
    if (mail) mail.hidden = true;
    resultWrap.hidden = true;
    status.textContent = '';
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!task.value.trim()) {
      task.setCustomValidity(copy.brief_required);
      task.reportValidity();
      return;
    }
    const data = new FormData(form);
    const sections = [
      [copy.brief_task, String(data.get('task') || '').trim()],
      [copy.brief_data, String(data.get('data') || '').trim()],
      [copy.brief_output, String(data.get('output') || '').trim()],
    ].filter(([, value]) => value);
    const brief = sections.map(([label, value]) => `${label}\n${value}`).join('\n\n');
    const snapshot = version;
    result.value = brief;
    resultWrap.hidden = false;
    status.textContent = copy.brief_ready;
    if (mail && copy.email) {
      mail.href = `mailto:${copy.email}?subject=${encodeURIComponent(copy.brief_subject)}&body=${encodeURIComponent(brief)}`;
      mail.hidden = false;
    }
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard is unavailable');
      await navigator.clipboard.writeText(brief);
      if (snapshot === version) status.textContent = copy.brief_copied;
    } catch {
      if (snapshot === version) {
        status.textContent = copy.brief_fallback;
        result.focus();
        result.select();
      }
    }
  });
})();/* Галерея и сравнение: независимы от конструктора задания. */
(() => {
  'use strict';
  document.querySelectorAll('[data-comparison]').forEach((container) => {
    const range = container.querySelector('[data-comparison-range]');
    const stage = container.querySelector('.comparison-stage');
    const controls = container.querySelector('[data-comparison-controls]');
    if (!range || !stage || !controls) return;
    const update = () => stage.style.setProperty('--split', `${Number(range.value)}%`);
    range.addEventListener('input', update);
    controls.hidden = false;
    update();
  });

  const dialog = document.getElementById('gallery-dialog');
  const links = [...document.querySelectorAll('[data-gallery]')];
  if (!dialog || !links.length || typeof dialog.showModal !== 'function') return;
  const stage = document.getElementById('viewer-stage');
  const caption = document.getElementById('viewer-caption');
  const counter = document.getElementById('viewer-count');
  const original = document.getElementById('viewer-original');
  const zoom = dialog.querySelector('[data-viewer-zoom]');
  let index = 0;
  let returnFocus = null;
  const show = (next) => {
    index = (next + links.length) % links.length;
    const link = links[index];
    const source = link.querySelector('img');
    const image = new Image();
    image.src = link.href;
    image.alt = source?.alt || '';
    image.decoding = 'async';
    stage.replaceChildren(image);
    stage.classList.remove('is-zoomed');
    stage.scrollTo(0, 0);
    zoom.setAttribute('aria-pressed', 'false');
    caption.textContent = link.dataset.caption || '';
    original.href = link.href;
    counter.textContent = `${index + 1} ${dialog.dataset.countWord} ${links.length}`;
  };
  links.forEach((link, i) => {
    link.addEventListener('click', (event) => {
      // Ctrl/Cmd-click сохраняет обычное открытие файла в новой вкладке.
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      returnFocus = link;
      show(i);
      if (!dialog.open) dialog.showModal();
      document.body.classList.add('modal-open');
    });
  });
  dialog.querySelector('[data-viewer-close]').addEventListener('click', () => dialog.close());
  dialog.querySelector('[data-viewer-previous]').addEventListener('click', () => show(index - 1));
  dialog.querySelector('[data-viewer-next]').addEventListener('click', () => show(index + 1));
  zoom.addEventListener('click', () => {
    const enabled = stage.classList.toggle('is-zoomed');
    zoom.setAttribute('aria-pressed', String(enabled));
    stage.scrollTo(0, 0);
  });
  dialog.addEventListener('keydown', (event) => {
    // В увеличенном изображении стрелки прокручивают сам рисунок.
    if (stage.classList.contains('is-zoomed') && event.target === stage) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); show(index + 1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); show(index - 1); }
  });
  dialog.addEventListener('click', (event) => {
    const rect = dialog.getBoundingClientRect();
    const outside = event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom;
    if (event.target === dialog && outside) dialog.close();
  });
  dialog.addEventListener('close', () => {
    if (!document.querySelector('dialog[open]')) document.body.classList.remove('modal-open');
    returnFocus?.focus({ preventScroll: true });
    stage.replaceChildren();
  });
})();