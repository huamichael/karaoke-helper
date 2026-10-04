/**
 * The tonearm, rendered with three.js over the record. Loaded on demand by
 * Tonearm.tsx, so three.js stays out of the first page load.
 *
 * The camera looks straight down (orthographic), so the arm lines up with the
 * flat record; depth comes from metal materials, a key and a fill light, a soft
 * cast shadow and contact shadows. Built like a real S-shaped arm: gimbal base,
 * anti-skate dial, cue lever, S-tube, headshell with a cartridge and finger lift,
 * a knurled counterweight, and an arm rest. It moves like one too: lift on the
 * cue lever, swing, set down; while playing, the stylus creeps slowly inward.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The tonearm"). Ported from frontend/prototype/index.html.
 */
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { armLayout } from "../../../logic/turntable";

export type ArmPlace = "play" | "rest" | "cue";

/** Where the sound button goes: the centre of the arm's pivot cap and the button's diameter, in the dial's pixels. */
export type CapPlace = { x: number; y: number; d: number };

export type TonearmScene = {
  /** Size the canvas to the dial and place the arm for this record. */
  layout(g: { cx: number; cy: number; R: number }, w: number, h: number): void;
  /** Move the arm. Resolves true once there, false if another move took over. */
  go(where: ArmPlace): Promise<boolean>;
  setAccent(color: string): void;
  /** Whether a point on screen falls on the arm, its base or its rest. */
  hit(clientX: number, clientY: number): boolean;
  setHover(on: boolean): void;
  dispose(): void;
};

const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const TUBE_Y = 22;

function roundedRect(w: number, h: number, r: number) {
  const s = new THREE.Shape();
  s.moveTo(-w / 2 + r, -h / 2); s.lineTo(w / 2 - r, -h / 2); s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
  s.lineTo(w / 2, h / 2 - r); s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2); s.lineTo(-w / 2 + r, h / 2);
  s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r); s.lineTo(-w / 2, -h / 2 + r); s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
  return s;
}

export function createTonearm(canvas: HTMLCanvasElement, accentColor: string, onCap: (place: CapPlace) => void): TonearmScene {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.03).texture;
  scene.environmentIntensity = 0.85;
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 4000);
  camera.up.set(0, 0, -1);
  camera.position.set(0, 2000, 0);
  camera.lookAt(0, 0, 0); // screen x = world x, screen y = world z

  scene.add(new THREE.HemisphereLight(0xf4f6ff, 0x1a1a22, 0.45));
  const key = new THREE.DirectionalLight(0xfff4e6, 2.6);
  key.position.set(-380, 820, -300);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.radius = 7;
  key.shadow.bias = -0.0003;
  key.shadow.normalBias = 0.6;
  const fill = new THREE.DirectionalLight(0xdde6ff, 0.7);
  fill.position.set(420, 380, 320);
  scene.add(key, key.target, fill);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(6000, 6000), new THREE.ShadowMaterial({ opacity: 0.4 }));
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  const brushed = new THREE.MeshPhysicalMaterial({ color: 0xc9cbd1, metalness: 1, roughness: 0.34, clearcoat: 0.25, clearcoatRoughness: 0.5 });
  const polished = new THREE.MeshStandardMaterial({ color: 0xc4c7ce, metalness: 1, roughness: 0.16 });
  const satin = new THREE.MeshStandardMaterial({ color: 0x25252b, metalness: 0.75, roughness: 0.42 });
  const matte = new THREE.MeshStandardMaterial({ color: 0x0f0f12, metalness: 0.2, roughness: 0.7 });
  const accent = new THREE.MeshStandardMaterial({ color: new THREE.Color(accentColor), metalness: 0.25, roughness: 0.4 });
  const cast = (...ms: THREE.Object3D[]) => ms.forEach((m) => { m.castShadow = true; });
  const mesh = (geo: THREE.BufferGeometry, mat: THREE.Material, x = 0, y = 0, z = 0) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    return m;
  };
  const alongX = (m: THREE.Mesh) => { m.rotation.z = Math.PI / 2; return m; };

  // a soft contact shadow, as a texture
  const cs = document.createElement("canvas");
  cs.width = cs.height = 128;
  const cg = cs.getContext("2d")!, grad = cg.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, "rgba(0,0,0,.55)");
  grad.addColorStop(1, "rgba(0,0,0,0)");
  cg.fillStyle = grad;
  cg.fillRect(0, 0, 128, 128);
  const contactMat = new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(cs), transparent: true, depthWrite: false });
  const contact = (size: number) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), contactMat);
    m.rotation.x = -Math.PI / 2;
    m.position.y = 0.5;
    return m;
  };

  // ---- the base
  const base = new THREE.Group();
  scene.add(base);
  const plinth = mesh(new THREE.CylinderGeometry(46, 49, 7, 96), satin, 0, 3.5);
  const plinthRim = mesh(new THREE.TorusGeometry(46.5, 1, 8, 96), polished, 0, 7);
  plinthRim.rotation.x = Math.PI / 2;
  const housing = mesh(new THREE.CylinderGeometry(25, 27, 24, 72), brushed, 0, 19);
  const CAP = { top: 19, h: 5 };
  const housingCap = mesh(new THREE.CylinderGeometry(CAP.top, 22, CAP.h, 72), polished, 0, 33.5);
  const accentRing = mesh(new THREE.TorusGeometry(34, 1.3, 10, 96), accent, 0, 7.6);
  accentRing.rotation.x = Math.PI / 2;
  const skate = new THREE.Group();
  skate.position.set(-31, 0, 31);
  skate.add(mesh(new THREE.CylinderGeometry(9, 9.5, 12, 40), matte, 0, 13), mesh(new THREE.CylinderGeometry(7, 7, 1.4, 40), polished, 0, 19.6), mesh(new THREE.BoxGeometry(1.4, 0.8, 6), accent, 0, 20.4, -3));
  const cue = new THREE.Group();
  cue.position.set(31, 0, 31);
  const cueLever = new THREE.Group();
  cueLever.position.y = 21;
  cueLever.add(mesh(new THREE.BoxGeometry(24, 3, 5), polished, 12), mesh(new THREE.SphereGeometry(3.6, 20, 16), matte, 24));
  cue.add(mesh(new THREE.CylinderGeometry(5, 6, 14, 32), satin, 0, 14), cueLever);
  base.add(contact(170), plinth, plinthRim, housing, housingCap, accentRing, skate, cue);
  cast(plinth, housing, housingCap, ...skate.children, ...cue.children, ...cueLever.children);

  // ---- the arm rest, where the arm sits while the record is stopped (placed in layout)
  const rest = new THREE.Group();
  scene.add(rest);
  const restClip = mesh(new THREE.TorusGeometry(6, 1.3, 8, 24, Math.PI), polished, 0, 24);
  restClip.rotation.y = Math.PI / 2;
  rest.add(contact(46), mesh(new THREE.CylinderGeometry(4.5, 5.5, 16, 32), satin, 0, 8), mesh(new THREE.BoxGeometry(8, 5, 20), matte, 0, 18), restClip);
  cast(...rest.children.slice(1));

  // ---- the arm: yaw swings it about the pivot, pitch tilts it up on the cue lever
  const yaw = new THREE.Group();
  yaw.position.y = TUBE_Y;
  base.add(yaw);
  const pitch = new THREE.Group();
  yaw.add(pitch);
  const gimbal = mesh(new THREE.BoxGeometry(20, 14, 28), brushed);
  const pins = alongX(mesh(new THREE.CylinderGeometry(3.2, 3.2, 36, 24), polished));
  pins.rotation.set(Math.PI / 2, 0, 0);
  pitch.add(gimbal, pins);
  cast(gimbal, pins);
  // counterweight, behind the pivot
  const stub = alongX(mesh(new THREE.CylinderGeometry(3.2, 3.2, 64, 24), polished, 40));
  const weight = alongX(mesh(new THREE.CylinderGeometry(17, 17, 32, 64), matte, 54));
  const knurl = [0, 1, 2, 3, 4].map((i) => alongX(mesh(new THREE.CylinderGeometry(17.6, 17.6, 1.6, 64), brushed, 41 + i * 6.5)));
  const index = alongX(mesh(new THREE.CylinderGeometry(13.5, 13.5, 2, 48), accent, 37));
  pitch.add(stub, weight, index, ...knurl);
  cast(stub, weight, ...knurl);
  // headshell, built round the stylus tip at its origin
  const head = new THREE.Group();
  pitch.add(head);
  const shell = mesh(new THREE.ExtrudeGeometry(roundedRect(52, 22, 5), { depth: 3, bevelEnabled: true, bevelThickness: 1, bevelSize: 1, bevelSegments: 3 }), brushed, 20, 15);
  shell.rotation.x = -Math.PI / 2;
  const cart = mesh(new THREE.BoxGeometry(24, 11, 17), matte, 13, 8);
  const cartStripe = mesh(new THREE.BoxGeometry(24.4, 2.6, 17.4), accent, 13, 12);
  const guard = mesh(new THREE.BoxGeometry(7, 5, 12), accent, 1, 3);
  const finger = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(6, 16, 10), new THREE.Vector3(-4, 17, 17), new THREE.Vector3(-14, 20, 19)]), 20, 1.6, 10), polished);
  const collar = alongX(mesh(new THREE.CylinderGeometry(5.6, 5.6, 12, 28), polished, 48, 17));
  head.add(shell, cart, cartStripe, guard, finger, collar);
  cast(shell, cart, guard, finger, collar);
  head.rotation.y = 0.38; // the headshell's offset angle
  let tube: THREE.Mesh | null = null, grip: THREE.Mesh | null = null;
  const gripMat = new THREE.MeshBasicMaterial({ visible: false });

  // phi: the arm's screen angle from the pivot; lift: cue-lever tilt; creep: drift inward while playing
  const ST = { phi: (184 * Math.PI) / 180, lift: 0, phiE: 0, phiR: (184 * Math.PI) / 180, LIFT: 0.05, creep: 0 };
  let raf = 0, creepTimer = 0, cancelTween: (() => void) | null = null, token = {};

  const render = () => renderer.render(scene, camera);
  const pose = () => {
    yaw.rotation.y = Math.PI - (ST.phi - ST.creep); // screen angle of the arm → rotation about y
    pitch.rotation.z = -ST.lift; // the front rises on the cue lever
    cueLever.rotation.y = (0.55 * ST.lift) / ST.LIFT;
  };

  function tween(prop: "phi" | "lift", to: number, dur: number, ease = easeInOut): Promise<boolean> {
    cancelTween?.();
    const from = ST[prop], t0 = performance.now();
    return new Promise((resolve) => {
      cancelTween = () => { cancelAnimationFrame(raf); cancelTween = null; resolve(false); };
      const frame = (now: number) => {
        const t = reducedMotion() ? 1 : Math.min(1, (now - t0) / dur);
        ST[prop] = from + (to - from) * ease(t);
        pose();
        render();
        if (t < 1) raf = requestAnimationFrame(frame);
        else { cancelTween = null; resolve(true); }
      };
      raf = requestAnimationFrame(frame);
    });
  }

  // while the stylus is in the groove, it creeps inward very slowly
  function creep(on: boolean) {
    clearInterval(creepTimer);
    if (!on) return;
    creepTimer = window.setInterval(() => {
      ST.creep = Math.min((5 * Math.PI) / 180, ST.creep + ((0.05 * Math.PI) / 180) * 0.1);
      pose();
      render();
    }, 100);
  }

  async function go(where: ArmPlace): Promise<boolean> {
    const mine = {};
    token = mine;
    const live = () => token === mine;
    creep(false);
    if (where === "cue") return tween("lift", ST.LIFT, 320, easeOut);
    const target = where === "rest" ? ST.phiR : ST.phiE;
    if (ST.lift < ST.LIFT * 0.98 && (!(await tween("lift", ST.LIFT, 340, easeOut)) || !live())) return false;
    if (ST.creep) { ST.phi -= ST.creep; ST.creep = 0; }
    if (Math.abs(ST.phi - target) > 0.002 && (!(await tween("phi", target, 380 + Math.abs(ST.phi - target) * 1500)) || !live())) return false;
    if (!(await tween("lift", 0, 560, easeOut)) || !live()) return false;
    if (where === "play") creep(true);
    return true;
  }

  function layout(g: { cx: number; cy: number; R: number }, w: number, h: number) {
    renderer.setSize(w, h, false);
    Object.assign(camera, { left: -w / 2, right: w / 2, top: h / 2, bottom: -h / 2 });
    camera.updateProjectionMatrix();
    Object.assign(key.shadow.camera, { left: -w, right: w, top: h, bottom: -h, near: 1, far: 3000 });
    key.shadow.camera.updateProjectionMatrix();
    const a = armLayout(g, w, h);
    base.position.set(a.pivot.x - w / 2, 0, a.pivot.y - h / 2);
    ST.phiE = a.playAngle;
    ST.phiR = a.restAngle;
    ST.LIFT = a.lift;
    const L = a.length;
    head.position.set(-L, 4 - TUBE_Y, 0);
    // the S-shaped tube, from the gimbal to the headshell collar
    head.updateMatrix();
    const c = new THREE.Vector3(48, 17, 0).applyMatrix4(head.matrix);
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-8, 0, 0), new THREE.Vector3(-L * 0.3, 0, -L * 0.03), new THREE.Vector3(-L * 0.62, 0, L * 0.008),
      new THREE.Vector3(c.x + 26, c.y * 0.6, c.z + L * 0.03), c,
    ]);
    if (tube && grip) { pitch.remove(tube, grip); tube.geometry.dispose(); grip.geometry.dispose(); }
    tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 220, 3.8, 28), polished);
    tube.castShadow = true;
    grip = new THREE.Mesh(new THREE.TubeGeometry(curve, 40, 14, 8), gripMat); // a fatter, invisible target for clicks
    pitch.add(tube, grip);
    rest.position.set(a.rest.x - w / 2, 0, a.rest.y - h / 2);
    rest.rotation.y = Math.PI - ST.phiR;
    pose();
    render();
    placeSound(w, h);
  }

  // The sound button sits on the gimbal's polished cap: project the cap's top face to the screen and centre the button on it.
  function placeSound(w: number, h: number) {
    scene.updateMatrixWorld();
    const toPx = (v: THREE.Vector3) => { const p = v.clone().project(camera); return { x: ((p.x + 1) / 2) * w, y: ((1 - p.y) / 2) * h }; };
    const at = toPx(housingCap.localToWorld(new THREE.Vector3(0, CAP.h / 2, 0)));
    const edge = toPx(housingCap.localToWorld(new THREE.Vector3(CAP.top, CAP.h / 2, 0)));
    const r = Math.hypot(edge.x - at.x, edge.y - at.y);
    onCap({ x: at.x, y: at.y, d: 2 * r - 8 }); // leave an even ring of polished metal round it
  }

  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  function hit(x: number, y: number) {
    const r = canvas.getBoundingClientRect();
    if (x < r.left || x > r.right || y < r.top || y > r.bottom) return false;
    ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    return ray.intersectObjects([base, rest], true).length > 0;
  }

  return {
    layout,
    go,
    hit,
    setAccent: (c) => { accent.color.set(c); render(); },
    setHover: (on) => { accent.emissive.setRGB(on ? 0.16 : 0, on ? 0.16 : 0, on ? 0.16 : 0); render(); },
    dispose: () => {
      cancelTween?.();
      clearInterval(creepTimer);
      scene.traverse((o) => {
        const m = o as THREE.Mesh;
        m.geometry?.dispose();
      });
      [brushed, polished, satin, matte, accent, contactMat, gripMat].forEach((m) => m.dispose());
      pmrem.dispose();
      renderer.dispose();
    },
  };
}
