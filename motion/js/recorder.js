window.JON = window.JON || {};

JON.Recorder = (function () {
  const CFG = JON.CFG;

  function stamp() {
    const d = new Date(), p = n => String(n).padStart(2, '0');
    return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + p(d.getHours()) + p(d.getMinutes());
  }

  function download(blob, name) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 8000);
  }

  const chan = typeof MessageChannel !== 'undefined' ? new MessageChannel() : null;
  let pending = null;
  if (chan) chan.port1.onmessage = () => { const r = pending; pending = null; if (r) r(); };
  const yieldToUi = chan
    ? () => new Promise(r => { pending = r; chan.port2.postMessage(0); })
    : () => new Promise(r => setTimeout(r, 0));

  function canMp4() {
    return typeof VideoEncoder === 'function' && typeof VideoFrame === 'function' &&
      typeof window.Mp4Muxer !== 'undefined';
  }

  async function videoConfig(w, h, bitrate) {
    const codecs = ['avc1.640034', 'avc1.4d0034', 'avc1.640028', 'avc1.42E01E'];
    const accel = ['prefer-hardware', 'no-preference'];
    for (const hw of accel) {
      for (const codec of codecs) {
        const cfg = {
          codec, width: w, height: h, bitrate: bitrate, framerate: CFG.FPS,
          hardwareAcceleration: hw, latencyMode: 'quality'
        };
        try {
          const s = await VideoEncoder.isConfigSupported(cfg);
          if (s.supported) return s.config || cfg;
        } catch (e) {  }
      }
    }
    return null;
  }

  async function mp4(o) {
    if (!canMp4()) throw new Error('Dieser Browser kann kein MP4 erzeugen (WebCodecs fehlt). Bitte Live-Aufnahme oder Bildfolge nutzen.');

    const W = o.canvas.width, H = o.canvas.height;
    const fps = CFG.FPS, total = Math.round(CFG.DURATION * fps);
    const vcfg = await videoConfig(W, H, o.bitrate || 20000000);
    if (!vcfg) throw new Error('Kein passender H.264-Encoder gefunden.');

    const { Muxer, ArrayBufferTarget } = window.Mp4Muxer;
    const buf = o.audioBuffer;
    const muxer = new Muxer({
      target: new ArrayBufferTarget(),
      fastStart: 'in-memory',
      firstTimestampBehavior: 'offset',
      video: { codec: 'avc', width: W, height: H, frameRate: fps },
      audio: buf ? { codec: 'aac', sampleRate: buf.sampleRate, numberOfChannels: buf.numberOfChannels } : undefined
    });

    if (buf && typeof AudioEncoder === 'function') {
      try {
        let aerr = null;
        const aenc = new AudioEncoder({
          output: (chunk, meta) => muxer.addAudioChunk(chunk, meta),
          error: e => { aerr = e; }
        });
        aenc.configure({
          codec: 'mp4a.40.2', sampleRate: buf.sampleRate,
          numberOfChannels: buf.numberOfChannels, bitrate: 192000
        });
        const CH = buf.numberOfChannels, SR = buf.sampleRate, BLK = 4800;
        const chans = [];
        for (let c = 0; c < CH; c++) chans.push(buf.getChannelData(c));
        for (let off = 0; off < buf.length; off += BLK) {
          const n = Math.min(BLK, buf.length - off);
          const data = new Float32Array(n * CH);
          for (let c = 0; c < CH; c++) data.set(chans[c].subarray(off, off + n), c * n);
          const ad = new AudioData({
            format: 'f32-planar', sampleRate: SR, numberOfFrames: n,
            numberOfChannels: CH, timestamp: Math.round(off / SR * 1e6), data
          });
          aenc.encode(ad); ad.close();
        }
        await aenc.flush(); aenc.close();
        if (aerr) throw aerr;
      } catch (e) {
        console.warn('Tonspur konnte nicht eingebettet werden:', e);
      }
    }

    let verr = null;
    const venc = new VideoEncoder({
      output: (chunk, meta) => muxer.addVideoChunk(chunk, meta),
      error: e => { verr = e; }
    });
    venc.configure(vcfg);

    const usPerFrame = 1e6 / fps;
    for (let i = 0; i < total; i++) {
      if (verr) break;
      o.renderFrame(i / fps, i);
      const frame = new VideoFrame(o.canvas, {
        timestamp: Math.round(i * usPerFrame),
        duration: Math.round(usPerFrame)
      });
      venc.encode(frame, { keyFrame: i % fps === 0 });
      frame.close();

      let guard = 0;
      while (venc.encodeQueueSize > 6 && guard++ < 100000) await yieldToUi();
      await yieldToUi();
      if (o.onTick && i % 4 === 0) o.onTick(i / total, 'MP4 · Bild ' + (i + 1) + ' / ' + total);
    }

    await venc.flush();
    venc.close();
    if (verr) throw verr;

    muxer.finalize();
    const blob = new Blob([muxer.target.buffer], { type: 'video/mp4' });
    const name = 'jon-motion-' + stamp() + '.mp4';
    download(blob, name);
    return { blob, name, frames: total, bytes: blob.size };
  }

  const CANDIDATES = [
    'video/mp4;codecs=avc1.640034,mp4a.40.2',
    'video/mp4;codecs=avc1.4d0034,mp4a.40.2',
    'video/mp4',
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm'
  ];

  function pick() {
    if (typeof MediaRecorder === 'undefined') return null;
    for (const m of CANDIDATES) if (MediaRecorder.isTypeSupported(m)) return m;
    return null;
  }

  const ext = mime => /mp4/.test(mime || '') ? 'mp4' : 'webm';

  const FFMPEG_MUX = 'ffmpeg -i jon-live.webm -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k jon.mp4';

  function live(o) {
    const mime = pick();
    if (!mime) throw new Error('Dieser Browser kann nicht live aufnehmen.');

    const stream = o.canvas.captureStream(CFG.FPS);
    if (o.audioStream) o.audioStream.getAudioTracks().forEach(t => stream.addTrack(t));

    const chunks = [];
    const rec = new MediaRecorder(stream, {
      mimeType: mime, videoBitsPerSecond: 24000000, audioBitsPerSecond: 192000
    });
    rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
    const stopped = new Promise(r => { rec.onstop = r; });
    rec.start(200);

    return {
      mime,
      async finish() {
        if (rec.state !== 'inactive') rec.stop();
        await stopped;
        stream.getVideoTracks().forEach(t => t.stop());
        const blob = new Blob(chunks, { type: mime });
        if (!blob.size) throw new Error('Der Encoder hat keine Daten geliefert. Bitte den MP4-Export verwenden.');
        const name = 'jon-live-' + stamp() + '.' + ext(mime);
        download(blob, name);
        return { name, bytes: blob.size, mime, hint: ext(mime) === 'mp4' ? null : FFMPEG_MUX };
      }
    };
  }

  const FFMPEG_SEQ = 'ffmpeg -framerate 60 -i frame_%05d.jpg -i jon-ton.wav -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -shortest jon.mp4';

  async function frames(o) {
    if (typeof window.showDirectoryPicker !== 'function')
      throw new Error('Bildfolgen brauchen Chrome oder Edge (Ordnerzugriff).');

    const dir = await window.showDirectoryPicker({ mode: 'readwrite' });
    const fps = CFG.FPS, total = Math.round(CFG.DURATION * fps);
    const type = o.png ? 'image/png' : 'image/jpeg';
    const suffix = o.png ? '.png' : '.jpg';

    for (let i = 0; i < total; i++) {
      o.renderFrame(i / fps, i);
      const blob = await new Promise(r => o.canvas.toBlob(r, type, 0.95));
      const fh = await dir.getFileHandle('frame_' + String(i).padStart(5, '0') + suffix, { create: true });
      const ws = await fh.createWritable();
      await ws.write(blob); await ws.close();
      await yieldToUi();
      if (o.onTick && i % 4 === 0) o.onTick(i / total, 'Bildfolge · ' + (i + 1) + ' / ' + total);
    }
    return { frames: total, hint: FFMPEG_SEQ };
  }

  return { mp4, live, frames, canMp4, pick, ext, download, FFMPEG_MUX, FFMPEG_SEQ };
})();
