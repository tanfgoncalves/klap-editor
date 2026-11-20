import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {faceCenter, fontStack, OUTLINE, PUSH_FRAC, pushAt} from './common';
import {Plan} from './types';

const clean = (w: string) => w.replace(/[,;:]+$/, '');
const strong = (w: string) => w.replace(/[^\wÀ-ÿ]/g, '').length >= 7 || /\d/.test(w);

export const Captions: React.FC<{plan: Plan}> = ({plan}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const t = frame / fps;
  const st = plan.style;
  const scene = plan.scenes.find((s) => t >= s.start && t < s.end) || plan.scenes[plan.scenes.length - 1];
  if (scene && scene.captions === false) return null;
  if (plan.title?.text && st.hideCaptionsUnderTitle && t >= plan.title.start && t < plan.title.end) return null;
  if (plan.cta && t >= plan.cta.start && st.hideCaptionsUnderCta !== false) return null;
  const cap = plan.captions.find((c) => t >= c.start && t < c.end);
  if (!cap || cap.hide) return null;
  const local = frame - Math.round(cap.start * fps);
  const p = spring({frame: local, fps, config: {damping: 11, stiffness: 240, mass: 0.6}});
  const size = st.captionSize || 60;
  const weight = st.captionWeight || 800;
  const accent = st.accent || '#ffe14d';
  const anim = st.captionAnim || 'fill';

  // ------------------------------------------------ uma palavra por vez (Yap)
  if (st.captionMode === 'word' || st.captionPlacement === 'face-side') {
    const w = cap.words[0];
    const fc = faceCenter(plan);
    const pv = pushAt(plan, t);
    const cx = fc.cx;
    const cy = fc.cy + pv * PUSH_FRAC;
    const f = {...fc.f, y: fc.f.y + pv * PUSH_FRAC};
    const z = scene?.zoom || 1;
    const wide = f.w * z > 0.42;
    const idx = plan.captions.indexOf(cap);
    const tilt = idx % 3 === 0 ? -3 : idx % 3 === 1 ? 2 : 0;
    const hi = w && strong(w.w);
    let pos: React.CSSProperties;
    if (wide || st.captionPlacement !== 'face-side') {
      const yy = Math.min(0.72, f.y + f.h + 0.05);
      pos = {left: 60, width: width - 120, top: height * yy, textAlign: 'center'};
    } else if (cx < 0.5) {
      pos = {left: Math.min(width - 440, (cx + (f.w * z) / 2) * width + 24), width: 440, top: cy * height - size * 0.55, textAlign: 'left'};
    } else {
      pos = {left: Math.max(24, (cx - (f.w * z) / 2) * width - 464), width: 440, top: cy * height - size * 0.55, textAlign: 'right'};
    }
    return (
      <div
        style={{
          position: 'absolute',
          ...pos,
          fontFamily: fontStack(st.font),
          fontWeight: weight,
          fontSize: hi ? size * 1.12 : size,
          lineHeight: 1,
          letterSpacing: -1,
          color: hi ? accent : st.captionColor || '#fff',
          transform: `scale(${0.55 + 0.45 * p}) rotate(${tilt * p}deg)`,
          opacity: Math.min(1, p * 1.6),
          textTransform: st.captionCase === 'upper' ? 'uppercase' : 'none',
          ...OUTLINE,
        }}
      >
        {w ? clean(w.w).replace(/[.!?]+$/, '') : ''}
      </div>
    );
  }

  // ------------------------------------------------ frase curta com a palavra falada destacada
  const inSplit = scene && scene.layout === 'split';
  let y = inSplit ? st.splitCaptionY ?? 0.5 : st.captionY ?? 0.62;
  // desvia do rosto: se a legenda cairia em cima da boca/queixo, desce para logo abaixo do queixo
  if (!inSplit && plan.face && scene && (scene.layout === 'full' || scene.layout === 'green')) {
    const fc = faceCenter(plan);
    const pv = pushAt(plan, t);
    let chin: number;
    if (scene.layout === 'green') {
      const s = scene.cutoutScale || st.cutoutScale || 0.8;
      chin = 1 - (1 - (fc.f.y + fc.f.h)) * s;
    } else {
      const z = scene.zoom || 1;
      chin = fc.cy + (fc.f.h / 2) * z + pv * PUSH_FRAC;
    }
    const top = fc.f.y - 0.02;
    const half = (size * 1.3) / height / 2;
    if (y + half > top && y - half < chin) y = Math.min(0.78, chin + half + 0.02);
  }
  const box = anim === 'pill';
  const words = cap.words.map((w, i) => {
    const active = t >= w.s;
    const nextS = cap.words[i + 1]?.s ?? cap.end;
    const now = t >= w.s && t < nextS;
    const wl = Math.round((t - w.s) * fps);
    const wp = now ? spring({frame: wl, fps, config: {damping: 12, stiffness: 300, mass: 0.5}}) : active ? 1 : 0;
    if (anim === 'box') {
      return (
        <span key={i} style={{display: 'inline-block', position: 'relative', margin: '0 13px', opacity: active ? 1 : 0.9}}>
          {now ? (
            <span
              style={{
                position: 'absolute',
                left: -9,
                right: -9,
                top: -1,
                bottom: -5,
                background: accent,
                borderRadius: 14,
                transform: `scale(${0.6 + 0.4 * wp}) rotate(-2deg)`,
                boxShadow: '0 8px 22px rgba(0,0,0,0.35)',
              }}
            />
          ) : null}
          <span
            style={{
              position: 'relative',
              color: now ? st.boxTextColor || '#111' : st.captionColor || '#fff',
              ...(now ? {} : OUTLINE),
              display: 'inline-block',
              transform: `scale(${now ? 1 + 0.08 * wp : 1})`,
            }}
          >
            {clean(w.w)}
          </span>
        </span>
      );
    }
    return (
      <span
        key={i}
        style={{
          display: 'inline-block',
          margin: '0 7px',
          color: box ? (now ? accent : st.captionColor) : now ? accent : st.captionColor || '#fff',
          opacity: active ? 1 : box ? 0.45 : 0.85,
          transform: `translateY(${now ? -6 * wp : 0}px) scale(${now ? 1 + 0.06 * wp : 1})`,
        }}
      >
        {clean(w.w)}
      </span>
    );
  });
  const out = interpolate(t, [cap.end - 0.08, cap.end], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div
      style={{
        position: 'absolute',
        left: 50,
        width: width - 100,
        top: height * y,
        transform: `translateY(-50%) scale(${0.8 + 0.2 * p})`,
        opacity: out,
        textAlign: 'center',
        fontFamily: fontStack(st.font),
        fontWeight: weight,
        fontSize: size,
        lineHeight: 1.22,
        textTransform: st.captionCase === 'upper' ? 'uppercase' : 'none',
        ...(anim === 'fill' ? OUTLINE : {}),
      }}
    >
      {box ? (
        <span
          style={{
            background: st.captionBoxColor || '#fff',
            padding: '10px 22px 14px',
            borderRadius: 999,
            boxDecorationBreak: 'clone',
            WebkitBoxDecorationBreak: 'clone',
            boxShadow: '0 10px 30px rgba(0,0,0,0.25)',
            lineHeight: 1.6,
          }}
        >
          {words}
        </span>
      ) : (
        words
      )}
    </div>
  );
};
