/* Xan CRM — vanilla JS interactions */

(function () {
  'use strict';

  // Spotlight radial-gradient effect for .xan-card elements.
  // Updates CSS custom properties --mx and --my on mousemove
  // so the ::before pseudo-element can position its gradient.
  function initSpotlight() {
    var cards = document.querySelectorAll('.xan-card');
    cards.forEach(function (card) {
      card.addEventListener('mousemove', function (e) {
        card.style.setProperty('--mx', e.offsetX + 'px');
        card.style.setProperty('--my', e.offsetY + 'px');
      });
    });
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSpotlight);
  } else {
    initSpotlight();
  }
})();
