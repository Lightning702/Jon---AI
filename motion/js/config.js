window.JON = window.JON || {};

JON.CFG = (function () {

  const WIDTH = 1080;
  const HEIGHT = 1920;
  const FPS = 60;
  const DURATION = 20.0;

  const T = { s1: 0.0, s2: 3.40, s3: 6.60, s4: 10.60, s5: 15.60, end: DURATION };

  const C = {
    gold:      0xd4af37,
    goldHi:    0xffd700,
    goldPale:  0xf7e4a8,
    goldDeep:  0x8a6d18,
    white:     0xffffff,
    ink:       0x040405,
    hologram:  0x9fd8ff
  };

  const FONT = '"Inter","Segoe UI",system-ui,sans-serif';
  const MONO = '"JetBrains Mono",Consolas,"Courier New",monospace';

  const TXT = {
    s1: 'Meet Jon',
    s2: 'Your personal AI',
    s3: ['Create.', 'Code.', 'Learn.'],
    s5a: 'One AI.',
    s5b: 'Unlimited possibilities.',
    url: 'getjon.info'
  };

  const SKILLS = [
    { icon: 'ai',      label: 'KI' },
    { icon: 'code',    label: 'Programmieren' },
    { icon: 'web',     label: 'Webseiten' },
    { icon: 'apps',    label: 'Apps' },
    { icon: 'chat',    label: 'Chat' },
    { icon: 'image',   label: 'Bilder' },
    { icon: 'automate',label: 'Automatisierung' }
  ];

  const ORBIT = [
    { icon: 'web',    label: 'Webseiten' },
    { icon: 'apps',   label: 'Apps' },
    { icon: 'game',   label: 'Spiele' },
    { icon: 'ai',     label: 'KI' },
    { icon: 'server', label: 'Server' },
    { icon: 'cloud',  label: 'Cloud' },
    { icon: 'code',   label: 'Code' }
  ];

  const CODE_LINES = [
    'const jon = new Assistant()',
    'await jon.build("website")',
    'jon.on("ask", answer)',
    'export default model',
    'if (idea) { ship(idea) }',
    'stream.pipe(response)',
    'render(<App />, root)',
    'def solve(problem): ...',
    'git commit -m "ship it"',
    'SELECT * FROM ideas',
    'npm run build --prod',
    'return possibilities'
  ];

  return {
    WIDTH, HEIGHT, FPS, DURATION, T, C, FONT, MONO, TXT, SKILLS, ORBIT, CODE_LINES,
    ASPECT: WIDTH / HEIGHT,

    CAM: { fov: 35, z: 8, near: 0.1, far: 120 }
  };
})();
