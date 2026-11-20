import React, {useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import {Plan} from './types';

const FONTS: [string, string, string, string][] = [
  ['Montserrat', 'fonts/montserrat-latin.woff2', 'normal', '100 900'],
  ['Inter Tight', 'fonts/inter-tight-latin.woff2', 'normal', '100 900'],
  ['Inter Tight', 'fonts/inter-tight-italic-latin.woff2', 'italic', '100 900'],
  ['Playfair Display', 'fonts/playfair-display-latin.woff2', 'normal', '400 900'],
  ['Playfair Display', 'fonts/playfair-display-italic-latin.woff2', 'italic', '400 900'],
  ['Caveat', 'fonts/caveat-latin.woff2', 'normal', '400 700'],
];

export const useFonts = () => {
  const [handle] = useState(() => delayRender('fontes'));
  useEffect(() => {
    Promise.all(
      FONTS.map(([fam, file, style, weight]) => {
        const f = new FontFace(fam, `url(${staticFile(file)}) format('woff2')`, {style, weight});
        return f.load().then((ff) => (document.fonts as any).add(ff)).catch(() => null);
      }),
    ).then(() => continueRender(handle));
  }, [handle]);
};

export const OUTLINE: React.CSSProperties = {
  WebkitTextStroke: '10px rgba(0,0,0,0.92)',
  paintOrder: 'stroke fill',
  textShadow: '0 6px 24px rgba(0,0,0,0.45)',
} as React.CSSProperties;

export const fontStack = (f?: string) => `'${f || 'Montserrat'}', 'Inter Tight', system-ui, sans-serif`;
export const EMOJI_FONT = `'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif`;

export const faceCenter = (plan: Plan) => {
  const f = plan.face || {x: 0.35, y: 0.2, w: 0.3, h: 0.18};
  return {cx: f.x + f.w / 2, cy: f.y + f.h / 2, f};
};

// partes da frase: *palavra* entre asteriscos vira destaque
export const splitMarked = (t: string) =>
  t.split(/(\*[^*]+\*)/g).filter(Boolean).map((p) => ({txt: p.replace(/^\*|\*$/g, ''), hi: /^\*.*\*$/.test(p)}));

// quanto a pessoa desce (0..1) para abrir espaço a um elemento em cima (cards, listas, busca...)
const PUSH_TYPES = ['card', 'list', 'search', 'counter', 'stamp', 'headline'];
export const pushAt = (plan: Plan, t: number) => {
  const f = plan.face;
  const scene = plan.scenes.find((s) => t >= s.start && t < s.end);
  if (!scene || (scene.layout !== 'full' && scene.layout !== undefined)) return 0;
  let v = 0;
  for (const o of plan.overlays || []) {
    const want = o.push ?? (PUSH_TYPES.includes(o.type) && (!f || f.y < 0.34));
    if (!want) continue;
    const a = Math.min(1, Math.max(0, (t - o.start + 0.05) / 0.32));
    const b = Math.min(1, Math.max(0, (o.end - t) / 0.28));
    const k = Math.min(a, b);
    v = Math.max(v, k * k * (3 - 2 * k));
  }
  return v;
};
export const PUSH_FRAC = 0.27;
