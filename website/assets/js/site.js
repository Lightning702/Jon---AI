const nav = document.getElementById('nav');
const toggle = document.querySelector('.nav__toggle');
const menu = document.getElementById('menu');

const setScrolled = () => nav && nav.classList.toggle('is-scrolled', window.scrollY > 8);
setScrolled();
window.addEventListener('scroll', setScrolled, { passive: true });

const setMenu = (open) => {
  if (!nav || !toggle) return;
  nav.classList.toggle('is-open', open);
  toggle.setAttribute('aria-expanded', String(open));
  toggle.setAttribute('aria-label', open ? 'Menü schließen' : 'Menü öffnen');
  document.body.classList.toggle('no-scroll', open);
};

if (toggle && menu) {
  toggle.addEventListener('click', () => setMenu(!nav.classList.contains('is-open')));
  menu.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && nav.classList.contains('is-open')) {
      setMenu(false);
      toggle.focus();
    }
  });
  window.matchMedia('(min-width: 981px)').addEventListener('change', (query) => {
    if (query.matches) setMenu(false);
  });
}

const reveals = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
  const revealer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      revealer.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -6% 0px', threshold: 0.04 });
  reveals.forEach((element) => revealer.observe(element));
  let pending = false;
  window.addEventListener('scroll', () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      document.querySelectorAll('.reveal:not(.is-visible)').forEach((element) => {
        if (element.getBoundingClientRect().top < window.innerHeight) element.classList.add('is-visible');
      });
    });
  }, { passive: true });
} else {
  reveals.forEach((element) => element.classList.add('is-visible'));
}

const spyOn = (links, rootMargin, onActive) => {
  const targets = links.map((link) => document.getElementById(link.hash.slice(1))).filter(Boolean);
  if (!targets.length || !('IntersectionObserver' in window)) return;
  const spy = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      links.forEach((link) => {
        const active = link.hash === `#${entry.target.id}`;
        link.classList.toggle('is-active', active);
        if (active && onActive) onActive(link);
      });
    });
  }, { rootMargin });
  targets.forEach((target) => spy.observe(target));
};

const samePage = (link) => link.hash && link.pathname === window.location.pathname;
spyOn([...document.querySelectorAll('.nav__links a')].filter(samePage), '-45% 0px -50% 0px');
spyOn([...document.querySelectorAll('.toc a')].filter(samePage), '-30% 0px -65% 0px', (link) => {
  const box = link.parentElement;
  if (window.matchMedia('(max-width: 980px)').matches) {
    box.scrollTo({ left: link.offsetLeft - 16, behavior: 'smooth' });
  } else if (box.scrollHeight > box.clientHeight) {
    box.scrollTo({ top: link.offsetTop - box.clientHeight / 2, behavior: 'smooth' });
  }
});

if (window.matchMedia('(hover: hover)').matches) {
  document.querySelectorAll('.card').forEach((card) => {
    card.addEventListener('pointermove', (event) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty('--mx', `${event.clientX - rect.left}px`);
      card.style.setProperty('--my', `${event.clientY - rect.top}px`);
    });
  });
}

document.querySelectorAll('[data-video]').forEach((box) => {
  const button = box.querySelector('.video__play');
  if (!button) return;
  button.addEventListener('click', () => {
    const frame = document.createElement('iframe');
    frame.src = `https://www.youtube-nocookie.com/embed/${box.dataset.video}?autoplay=1&rel=0`;
    frame.title = box.dataset.title || 'Video';
    frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    frame.allowFullscreen = true;
    box.appendChild(frame);
    button.remove();
    frame.focus();
  });
});

const year = document.getElementById('jahr');
if (year) year.textContent = String(new Date().getFullYear());
