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

  const musicToggle = document.getElementById('music-toggle');
  const bgAudio = document.getElementById('bg-audio');
  if (musicToggle && bgAudio) {
    const setPlaying = (playing) => {
      musicToggle.classList.toggle('playing', playing);
      musicToggle.setAttribute('aria-pressed', String(playing));
    };
    if (localStorage.getItem('vibrup-music') === 'on') {
      bgAudio.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
    }
    musicToggle.addEventListener('click', () => {
      if (bgAudio.paused) {
        bgAudio.play().then(() => {
          setPlaying(true);
          localStorage.setItem('vibrup-music', 'on');
        }).catch(() => setPlaying(false));
      } else {
        bgAudio.pause();
        setPlaying(false);
        localStorage.setItem('vibrup-music', 'off');
      }
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
