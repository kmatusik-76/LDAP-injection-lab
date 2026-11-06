// Konfetti po ukończeniu wszystkich zadań. Bez zewnętrznych bibliotek,
// żeby lab działał w pełni offline. Rysuje na płótnie nad stroną
// (bez blokowania kliknięć) i po kilku sekundach samo się usuwa.
(function () {
  "use strict";

  // Użytkownicy z wyłączonymi animacjami w systemie nie dostają konfetti.
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var COLORS = ["#1f7a4d", "#2f5fdb", "#f2b705", "#b4232a", "#5b3cc4", "#24a0ed"];
  var COUNT = 220;
  var DURATION_MS = 4500;   // jak długo spadają nowe kawałki
  var FADE_MS = 1200;       // wygaszanie na końcu

  var canvas = document.createElement("canvas");
  canvas.setAttribute("aria-hidden", "true");
  canvas.style.cssText =
    "position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:1000";
  document.body.appendChild(canvas);
  var ctx = canvas.getContext("2d");

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  function rand(min, max) { return min + Math.random() * (max - min); }

  // Dwa "działka" z dolnych rogów ekranu strzelające ku środkowi.
  function makePiece(fromLeft) {
    return {
      x: fromLeft ? rand(0, canvas.width * 0.1) : rand(canvas.width * 0.9, canvas.width),
      y: canvas.height + 10,
      vx: (fromLeft ? 1 : -1) * rand(3, 9),
      vy: -rand(12, 20),
      w: rand(6, 11),
      h: rand(8, 16),
      angle: rand(0, Math.PI * 2),
      spin: rand(-0.25, 0.25),
      tilt: rand(0, Math.PI * 2),
      color: COLORS[Math.floor(Math.random() * COLORS.length)]
    };
  }

  var pieces = [];
  for (var i = 0; i < COUNT; i++) pieces.push(makePiece(i % 2 === 0));

  var start = performance.now();
  var last = start;

  function frame(now) {
    var elapsed = now - start;
    // Ruch liczymy względem czasu, a nie liczby klatek, żeby animacja miała
    // tę samą prędkość na monitorach 60 Hz i 144 Hz. 1 = jedna klatka 60 Hz.
    var dt = Math.min((now - last) / (1000 / 60), 3);
    last = now;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.globalAlpha = elapsed > DURATION_MS
      ? Math.max(0, 1 - (elapsed - DURATION_MS) / FADE_MS)
      : 1;

    for (var i = 0; i < pieces.length; i++) {
      var p = pieces[i];
      p.vy = Math.min(p.vy + 0.35 * dt, 3.5);    // grawitacja, powolne opadanie
      p.vx *= Math.pow(0.99, dt);                // opór powietrza
      p.x += (p.vx + Math.sin(p.tilt) * 0.8) * dt;
      p.y += p.vy * dt;
      p.angle += p.spin * dt;
      p.tilt += 0.05 * dt;

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.angle);
      ctx.scale(1, Math.cos(p.tilt));  // efekt obracającego się papierka
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    }

    if (elapsed < DURATION_MS + FADE_MS) {
      requestAnimationFrame(frame);
    } else {
      window.removeEventListener("resize", resize);
      canvas.remove();
    }
  }
  requestAnimationFrame(frame);
})();
