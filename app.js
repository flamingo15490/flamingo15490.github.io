'use strict';
const menu = document.querySelector('.menu-button');
if (menu) menu.addEventListener('click', () => {
  const expanded = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(expanded));
  menu.setAttribute('aria-label', expanded ? '收起导航' : '展开导航');
  document.querySelector('.site-header nav').classList.toggle('open', expanded);
});
const filters = [...document.querySelectorAll('.filter')];
const search = document.querySelector('#search');
let category = '全部';
function filterArticles() {
  let count = 0;
  const query = search.value.trim().toLocaleLowerCase();
  document.querySelectorAll('.article-item').forEach(item => {
    const visible = (category === '全部' || item.dataset.category === category) && item.dataset.search.toLocaleLowerCase().includes(query);
    item.hidden = !visible;
    if (visible) count++;
  });
  document.querySelector('.result-count').textContent = `共 ${count} 篇文章`;
  document.querySelector('.empty-state').hidden = count !== 0;
}
filters.forEach(button => button.addEventListener('click', () => {
  category = button.dataset.category;
  filters.forEach(filter => {
    const selected = filter === button;
    filter.classList.toggle('selected', selected);
    filter.setAttribute('aria-pressed', String(selected));
  });
  filterArticles();
}));
if (search) search.addEventListener('input', filterArticles);
const outline = document.querySelector('.reading-outline');
if (outline) {
  const details = outline.querySelector('details');
  if (window.matchMedia('(max-width: 860px)').matches) details.open = false;
  const links = [...outline.querySelectorAll('nav a')];
  const sections = links.map(link => document.getElementById(link.hash.slice(1))).filter(Boolean);
  const mark = id => links.forEach(link => {
    if (link.hash === '#' + id) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
  if (sections.length) mark(sections[0].id);
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting);
      if (visible.length) mark(visible[0].target.id);
    }, {rootMargin:'-110px 0px -65% 0px',threshold:0});
    sections.forEach(section => observer.observe(section));
  }
}

document.querySelectorAll('[data-tex]').forEach(element => {
  if (window.katex) katex.render(element.dataset.tex, element, {
    displayMode: element.classList.contains('display'),
    throwOnError: false, strict: 'ignore', trust: false,
    output: 'htmlAndMathml'
  });
});
const progress = document.querySelector('.reading-progress');
if (progress) {
  const updateProgress = () => {
    const available = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = `${available > 0 ? Math.min(100, window.scrollY / available * 100) : 0}%`;
  };
  window.addEventListener('scroll', updateProgress, {passive:true});
  window.addEventListener('resize', updateProgress);
  updateProgress();
}
