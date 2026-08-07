(function () {
  const CFG = JON.CFG;
  const $ = id => document.getElementById(id);

  if (typeof THREE === 'undefined' || typeof gsap === 'undefined') {
    $('fatal').hidden = false;
    return;
  }

  const canvas = $('view');
  let pipe, world, tl, audio;
  let recording = false, live = null;

  async function init() {

    const fonts = document.fonts ? Promise.all([
      document.fonts.load('200 100px Inter'), document.fonts.load('800 100px Inter'),
      document.fonts.load('500 100px Inter'), document.fonts.load('400 40px "JetBrains Mono"')
    ]).then(() => document.fonts.ready) : Promise.resolve();
    await Promise.race([fonts, new Promise(r => setTimeout(r, 3000))]);

    pipe = new JON.GFX.Pipeline(canvas);
    world = new JON.World();
    JON.resetWorld(world);
    tl = JON.buildTimeline(world);
    audio = new JON.Audio();

    gsap.ticker.lagSmoothing(0);
    tl.pause(0);

    const baseLook = world.look.bind(world);
    world.look = t => {
      const l = baseLook(t);
      l.bloom *= parseFloat($('bloom').value);
      l.grain *= parseFloat($('grain').value);
      return l;
    };

    applyScale(1);
    wire();

    [0.4, CFG.T.s2 + .4, CFG.T.s3 + .4, CFG.T.s4 + .4, CFG.T.s5 + .4].forEach(t => { tl.time(t); draw(t); });
    seek(0);

    $('boot').classList.add('gone');
    if (!JON.Recorder.canMp4()) {
      $('btnMp4').disabled = true;
      $('btnMp4').title = 'Dieser Browser kann kein MP4 erzeugen (WebCodecs fehlt) – bitte Chrome oder Edge verwenden.';
    }
    if (!JON.Recorder.pick()) $('btnLive').disabled = true;

    JON.app = { tl, world, pipe, audio, seek, draw, canvas };

    loop();
  }

  function draw(t) {
    world.update(t);
    pipe.render(world.scene, world.camera, world.look(t));
  }

  function seek(t) {
    tl.time(Math.max(0, Math.min(CFG.DURATION, t)));
    draw(tl.time());
    ui();
  }

  function applyScale(s) {
    const w = Math.round(CFG.WIDTH * s / 2) * 2;
    const h = Math.round(CFG.HEIGHT * s / 2) * 2;
    pipe.setSize(w, h);
    world.particles.u.uPixel.value = h;
    $('res').textContent = w + '×' + h;
  }

  let fpsAcc = 0, fpsCount = 0, fpsLast = performance.now();
  function loop() {
    requestAnimationFrame(loop);
    if (recording === 'export') return;

    draw(tl.time());
    if (!tl.paused()) ui();
    if (recording === 'live' && tl.time() >= CFG.DURATION - 0.001) stopLive();

    const now = performance.now();
    fpsAcc += now - fpsLast; fpsLast = now; fpsCount++;
    if (fpsAcc > 500) {
      $('fps').textContent = Math.round(1000 / (fpsAcc / fpsCount)) + ' fps';
      fpsAcc = 0; fpsCount = 0;
    }
  }

  const fmt = t => String(Math.floor(t / 60)).padStart(2, '0') + ':' +
    String(Math.floor(t % 60)).padStart(2, '0') + '.' +
    String(Math.floor(t * 100 % 100)).padStart(2, '0');

  function ui() {
    const t = tl.time(), sc = $('scrub');
    sc.value = t;
    sc.style.setProperty('--p', (t / CFG.DURATION * 100) + '%');
    $('tcode').textContent = fmt(t) + ' / ' + fmt(CFG.DURATION);
    $('btnPlay').textContent = tl.paused() ? '▶ Abspielen' : '❚❚ Pause';
  }

  function play() {
    if (tl.time() >= CFG.DURATION - 0.01) tl.time(0);
    tl.play();
    if (!audio.muted) audio.play(tl.time());
    ui();
  }
  function pause() { tl.pause(); audio.stop(); ui(); }

  function wire() {
    $('btnPlay').onclick = () => tl.paused() ? play() : pause();
    $('btnRestart').onclick = () => { const running = !tl.paused(); audio.stop(); tl.pause(); seek(0); if (running) play(); };
    $('btnMute').onclick = () => {
      audio.setMuted(!audio.muted);
      $('btnMute').textContent = audio.muted ? '🔇' : '🔊';
      if (audio.muted) audio.stop();
      else if (!tl.paused()) audio.play(tl.time());
    };
    $('scrub').oninput = e => { audio.stop(); tl.pause(); seek(parseFloat(e.target.value)); };
    $('quality').onchange = e => applyScale(parseFloat(e.target.value));
    $('btnMp4').onclick = exportMp4;
    $('btnLive').onclick = () => recording === 'live' ? stopLive() : startLive();
    $('btnFrames').onclick = exportFrames;
    $('btnWav').onclick = exportWav;

    document.addEventListener('keydown', e => {
      if (/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
      const k = e.key.toLowerCase();
      if (k === ' ') { e.preventDefault(); tl.paused() ? play() : pause(); }
      else if (k === 'r') { audio.stop(); tl.pause(); seek(0); }
      else if (k === 'm') $('btnMute').click();
      else if (k === 'h') document.body.classList.toggle('clean');
      else if ('12345'.indexOf(k) >= 0) { audio.stop(); tl.pause(); seek([0, CFG.T.s2, CFG.T.s3, CFG.T.s4, CFG.T.s5][+k - 1]); }
    });
  }

  function progress(p, label) {
    $('recBar').hidden = false;
    $('recFill').style.width = (p * 100).toFixed(1) + '%';
    $('recTxt').textContent = label;
  }
  function lock(on, keepLive) {
    ['btnPlay', 'btnRestart', 'btnMp4', 'btnFrames', 'btnWav', 'scrub', 'quality', 'bitrate']
      .forEach(id => $(id).disabled = on);
    $('btnLive').disabled = on && !keepLive;
  }

  async function startLive() {
    try {
      if (!audio.muted) audio.ensure();
      live = JON.Recorder.live({
        canvas: canvas,
        audioStream: (!audio.muted && audio.streamDest) ? audio.streamDest.stream : null
      });
    } catch (err) { progress(0, 'Fehler: ' + err.message); return; }

    recording = 'live';
    $('btnLive').classList.add('on');
    $('btnLive').innerHTML = '■ Stopp';
    lock(true, true);

    audio.stop(); tl.pause(0); draw(0);
    await new Promise(r => setTimeout(r, 150));
    tl.play(0);
    if (!audio.muted) audio.play(0);

    progress(0, 'Aufnahme laeuft …');
    const tick = setInterval(() => {
      if (recording !== 'live') return clearInterval(tick);
      progress(tl.time() / CFG.DURATION, 'Aufnahme · ' + fmt(tl.time()));
    }, 100);
  }

  async function stopLive() {
    if (!live) return;
    const s = live; live = null; recording = false;
    tl.pause(); audio.stop();
    $('btnLive').classList.remove('on');
    $('btnLive').innerHTML = '● Live-Aufnahme';
    progress(1, 'Datei wird geschrieben …');
    try {
      const info = await s.finish();
      progress(1, info.name + ' · ' + (info.bytes / 1048576).toFixed(1) + ' MB');
      if (info.hint) console.info('In MP4 umwandeln:\n' + info.hint);
    } catch (err) {
      progress(0, 'Fehler: ' + err.message);
    }
    lock(false);
  }

  async function exportMp4() {
    if (recording) return;
    recording = 'export';
    lock(true); $('btnLive').disabled = true;
    audio.stop(); tl.pause(0);
    try {
      progress(0.02, 'Tonspur wird gerendert …');
      let buffer = null;
      try { buffer = await audio.renderBuffer(48000); }
      catch (e) { console.warn('Tonspur uebersprungen:', e); }

      const info = await JON.Recorder.mp4({
        canvas: canvas,
        audioBuffer: buffer,
        bitrate: parseInt($('bitrate').value, 10),
        renderFrame: t => { tl.time(t); draw(t); },
        onTick: (p, label) => progress(p, label)
      });
      progress(1, info.name + ' · ' + info.frames + ' Bilder · ' + (info.bytes / 1048576).toFixed(1) + ' MB');
    } catch (err) {
      progress(0, 'Abbruch: ' + err.message);
      console.error(err);
    }
    recording = false; lock(false); $('btnLive').disabled = false; seek(0);
  }

  async function exportFrames() {
    if (recording) return;
    recording = 'export';
    lock(true); $('btnLive').disabled = true;
    audio.stop(); tl.pause(0);
    try {
      const info = await JON.Recorder.frames({
        canvas: canvas,
        renderFrame: t => { tl.time(t); draw(t); },
        onTick: (p, label) => progress(p, label)
      });
      progress(1, info.frames + ' Bilder geschrieben');
      console.info('Zusammensetzen mit:\n' + info.hint);
    } catch (err) {
      progress(0, err.name === 'AbortError' ? 'Abgebrochen' : 'Fehler: ' + err.message);
    }
    recording = false; lock(false); $('btnLive').disabled = false; seek(0);
  }

  async function exportWav() {
    $('btnWav').disabled = true;
    progress(0.35, 'Tonspur wird gerendert …');
    try {
      const blob = await audio.renderWav(48000);
      JON.Recorder.download(blob, 'jon-ton.wav');
      progress(1, 'jon-ton.wav · ' + (blob.size / 1048576).toFixed(1) + ' MB');
    } catch (err) { progress(0, 'Fehler: ' + err.message); }
    $('btnWav').disabled = false;
  }

  init();
})();
