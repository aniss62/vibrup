document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.menu-toggle');
  const header = document.querySelector('header');
  if (toggle && header) {
    toggle.addEventListener('click', () => {
      header.classList.toggle('open');
    });
    document.querySelectorAll('.nav-links a').forEach((link) => {
      link.addEventListener('click', () => header.classList.remove('open'));
    });
  }

  const pills = document.querySelectorAll('.filter-pill');
  const cards = document.querySelectorAll('[data-category]');
  if (pills.length && cards.length) {
    pills.forEach((pill) => {
      pill.addEventListener('click', () => {
        pills.forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        const category = pill.dataset.filter;
        cards.forEach((card) => {
          const match = category === 'toutes' || card.dataset.category === category;
          card.style.display = match ? '' : 'none';
        });
      });
    });
  }
});
