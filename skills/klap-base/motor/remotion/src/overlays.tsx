import React from 'react';
import {AbsoluteFill, Easing, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {EMOJI_FONT, faceCenter, fontStack, OUTLINE} from './common';
import {MediaFill} from './layouts';
import {Overlay, Plan, Scene} from './types';

// entrada/saída padrão de um elemento que vive entre start e end (s)
const useLife = (start: number, end: number, stiff = 180) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - Math.round(start * fps);
  const p = spring({frame: local, fps, config: {damping: 12, stiffness: stiff, mass: 0.7}});
  const out = interpolate(frame, [end * fps - 7, end * fps], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return {p, out, local, fps, frame};
};

// ---------------------------------------------------------------- título
const Marked: React.FC<{text: string; hl?: string; color: string; prog: number}> = ({text, hl, color, prog}) => {
  if (!hl || !text.toLowerCase().includes(hl.toLowerCase())) return <>{text}</>;
  const i = text.toLowerCase().indexOf(hl.toLowerCase());
  const a = text.slice(0, i), b = text.slice(i, i + hl.length), c = text.slice(i + hl.length);
  return (
    <>
      {a}
      <span style={{position: 'relative', display: 'inline-block', WebkitTextStroke: '0px', textShadow: 'none', color: '#111'}}>
        <span
          style={{
            position: 'absolute',
            left: -10,
            right: -10,
            top: '8%',
            bottom: '2%',
            background: color,
            borderRadius: 10,
            transform: `scaleX(${prog}) rotate(-1.5deg)`,
            transformOrigin: '0% 50%',
          }}
        />
        <span style={{position: 'relative'}}>{b}</span>
      </span>
      {c}
    </>
  );
};

export const Title: React.FC<{plan: Plan}> = ({plan}) => {
  const {width, height} = useVideoConfig();
  const t = plan.title;
  const st = plan.style;
  const {p, out, local, fps} = useLife(t?.start || 0, t?.end || 0, 140);
  if (!t || !t.text) return null;
  const hlProg = interpolate(local, [8, 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const mode = st.titleStyle || 'outline';
  const base: React.CSSProperties = {
    position: 'absolute',
    left: 64,
    width: width - 128,
    textAlign: 'center',
    fontFamily: fontStack(st.titleFont || st.font),
    fontStyle: st.titleItalic ? 'italic' : 'normal',
    fontWeight: st.titleWeight || 800,
    fontSize: st.titleSize || 70,
    lineHeight: 1.1,
    opacity: Math.min(1, p * 1.4) * out,
    transform: `translateY(${(1 - p) * -36}px) scale(${0.94 + 0.06 * p})`,
  };
  const accent = st.titleHighlightColor || st.accent || '#ffe14d';
  if (mode === 'card') {
    return (
      <div style={{...base, top: height * (st.titleY ?? 0.12)}}>
        <span
          style={{
            background: st.accent || '#b3123a',
            color: '#fff',
            padding: '16px 30px 22px',
            borderRadius: 22,
            boxDecorationBreak: 'clone',
            WebkitBoxDecorationBreak: 'clone',
            lineHeight: 1.52,
            boxShadow: '0 18px 40px rgba(0,0,0,0.35)',
          }}
        >
          {t.text}
        </span>
      </div>
    );
  }
  if (mode === 'above-head') {
    const {f} = faceCenter(plan);
    const bottom = height - Math.max(height * 0.07, f.y * height - 24);
    return (
      <div style={{...base, top: undefined, bottom, color: '#fff', ...OUTLINE, WebkitTextStroke: '9px rgba(0,0,0,0.9)'}}>
        <Marked text={t.text} hl={t.highlight} color={accent} prog={hlProg} />
      </div>
    );
  }
  return (
    <div style={{...base, top: height * (st.titleY ?? 0.12), color: '#fff', ...OUTLINE}}>
      <Marked text={t.text} hl={t.highlight} color={accent} prog={hlProg} />
    </div>
  );
};

// ---------------------------------------------------------------- palavra-chave da cena
export const Keyword: React.FC<{plan: Plan; scene: Scene}> = ({plan, scene}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  if (!scene.keyword) return null;
  const st = plan.style;
  const tt = plan.title;
  const gt = scene.start + frame / fps;
  if (tt && tt.text && gt >= tt.start && gt < tt.end && scene.layout !== 'word') return null;
  const p = spring({frame, fps, config: {damping: 13, stiffness: 170}});
  const isCard = scene.layout === 'word';
  const kw = scene.keyword;
  const base = st.keywordSize || 120;
  const size = Math.min(base, ((width - 100) / Math.max(4, kw.length)) * 1.9);
  // acima da cabeça quando cabe; senão na altura do estilo
  const {f} = faceCenter(plan);
  const z = scene.zoom || 1;
  const headTop = (f.y - f.h * 0.25 * z) * height;
  const above = !isCard && headTop - size * 1.25 > height * 0.05;
  const posStyle: React.CSSProperties = isCard
    ? {top: height * 0.38}
    : above
      ? {bottom: height - headTop + 10}
      : {top: height * (st.keywordY ?? 0.2)};
  let li = 0;
  const wordsK = kw.split(' ');
  return (
    <div
      style={{
        position: 'absolute',
        left: 50,
        width: width - 100,
        ...posStyle,
        textAlign: 'center',
        fontFamily: fontStack(st.keywordFont || st.font),
        fontStyle: st.keywordItalic ? 'italic' : 'normal',
        fontWeight: 800,
        fontSize: size,
        lineHeight: 1.0,
        color: st.keywordColor || '#fff',
        textShadow: isCard ? 'none' : '0 8px 30px rgba(0,0,0,0.55)',
      }}
    >
      {wordsK.map((wd, wi) => (
        <span key={wi} style={{display: 'inline-block', whiteSpace: 'nowrap', marginRight: wi < wordsK.length - 1 ? size * 0.25 : 0}}>
          {wd.split('').map((ch, i) => {
            const k = li++;
            const lp = spring({frame: frame - k * 1.2, fps, config: {damping: 14, stiffness: 200}});
            return (
              <span key={i} style={{display: 'inline-block', opacity: lp, transform: `translateY(${(1 - lp) * 50}px) rotate(${(1 - lp) * 8}deg)`}}>
                {ch}
              </span>
            );
          })}
        </span>
      ))}
      <div
        style={{
          height: 8,
          margin: '14px auto 0',
          width: `${Math.min(80, kw.length * 7)}%`,
          background: st.accent || '#ffe14d',
          borderRadius: 8,
          transform: `scaleX(${interpolate(frame, [6, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})`,
          opacity: p,
        }}
      />
    </div>
  );
};

// ---------------------------------------------------------------- elementos que aparecem por cima
const OverlayItem: React.FC<{plan: Plan; o: Overlay}> = ({plan, o}) => {
  const {width, height} = useVideoConfig();
  const {p, out, local, fps, frame} = useLife(o.start, o.end);
  const st = plan.style;
  const accent = o.color || st.accent || '#ffe14d';
  const x = (o.x ?? 0.5) * width;
  const y = (o.y ?? 0.2) * height;
  const w = (o.w ?? 0.6) * width;
  const center = (inner: React.ReactNode, extra: React.CSSProperties = {}) => (
    <div style={{position: 'absolute', left: x - w / 2, top: y, width: w, transform: 'translateY(-50%)', ...extra}}>{inner}</div>
  );
  const float = Math.sin((frame / fps) * 2.4 + o.start) * 6;

  if (o.type === 'emoji') {
    const size = o.size || 170;
    return (
      <div
        style={{
          position: 'absolute',
          left: x - size / 2,
          top: y - size / 2 + float,
          width: size,
          height: size,
          fontSize: size * 0.86,
          lineHeight: `${size}px`,
          textAlign: 'center',
          fontFamily: EMOJI_FONT,
          transform: `scale(${p * out}) rotate(${(1 - p) * -25 + (o.rot || 0)}deg)`,
          filter: 'drop-shadow(0 14px 22px rgba(0,0,0,0.35))',
        }}
      >
        {o.emoji}
      </div>
    );
  }

  if (o.type === 'card') {
    const len = Math.round((o.end - o.start) * fps);
    const m = o.media ? plan.media[o.media] : undefined;
    const ratio = m && (m as any).h && (m as any).w ? (m as any).h / (m as any).w : 0.75;
    const h = Math.min(height * 0.42, w * (o.size || ratio));
    return (
      <div
        style={{
          position: 'absolute',
          left: x - w / 2,
          top: y - h / 2 + float,
          width: w,
          height: h,
          borderRadius: 28,
          overflow: 'hidden',
          border: '8px solid #fff',
          boxShadow: '0 30px 70px rgba(0,0,0,0.5)',
          transform: `scale(${p * out}) rotate(${(o.rot ?? -4) * p}deg)`,
          background: '#222',
        }}
      >
        <MediaFill plan={plan} mediaId={o.media} len={len} kenburns />
        {o.label ? (
          <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, padding: '14px 18px', background: 'linear-gradient(transparent, rgba(0,0,0,0.75))', color: '#fff', font: `700 34px ${fontStack(st.font)}`}}>
            {o.label}
          </div>
        ) : null}
      </div>
    );
  }

  if (o.type === 'notif') {
    const ny = interpolate(p, [0, 1], [-260, 0]);
    return (
      <div
        style={{
          position: 'absolute',
          left: 40,
          right: 40,
          top: (o.y ?? 0.05) * height + ny,
          opacity: out,
          borderRadius: 34,
          padding: '22px 26px',
          background: 'rgba(246,246,248,0.97)',
          boxShadow: '0 20px 50px rgba(0,0,0,0.35)',
          display: 'flex',
          gap: 22,
          alignItems: 'center',
          fontFamily: "-apple-system, 'SF Pro Text', 'Inter Tight', system-ui, sans-serif",
          color: '#111',
        }}
      >
        <div style={{width: 84, height: 84, borderRadius: 20, background: accent, display: 'grid', placeItems: 'center', fontSize: 50, fontFamily: EMOJI_FONT, flex: 'none'}}>
          {o.icon || '💬'}
        </div>
        <div style={{flex: 1, minWidth: 0}}>
          <div style={{display: 'flex', justifyContent: 'space-between', fontSize: 26, color: '#555', fontWeight: 600}}>
            <span>{(o.app || 'Mensagens').toUpperCase()}</span>
            <span>agora</span>
          </div>
          <div style={{fontSize: 36, fontWeight: 800, marginTop: 4}}>{o.title}</div>
          <div style={{fontSize: 32, marginTop: 2, color: '#222'}}>{o.text}</div>
        </div>
      </div>
    );
  }

  if (o.type === 'search') {
    const txt = o.text || '';
    const typed = Math.floor(interpolate(local, [6, 6 + Math.max(10, txt.length * 1.6)], [0, txt.length], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
    const caret = Math.floor(frame / 8) % 2 === 0;
    return center(
      <div
        style={{
          background: '#fff',
          borderRadius: 999,
          padding: '26px 36px',
          display: 'flex',
          alignItems: 'center',
          gap: 22,
          boxShadow: '0 24px 60px rgba(0,0,0,0.4)',
          fontFamily: "'Inter Tight', system-ui, sans-serif",
          fontSize: 50,
          color: '#111',
          transform: `scale(${p}) translateY(${(1 - p) * 40}px)`,
          opacity: out,
        }}
      >
        <svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="#666" strokeWidth="2.6" strokeLinecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-4-4" />
        </svg>
        <span style={{whiteSpace: 'nowrap', overflow: 'hidden'}}>
          {txt.slice(0, typed)}
          <span style={{opacity: caret ? 1 : 0, color: accent === '#ffe14d' ? '#1a73e8' : accent}}>|</span>
        </span>
      </div>,
      {width: Math.max(w, 0.86 * width), left: width * 0.07},
    );
  }

  if (o.type === 'counter') {
    const from = o.from ?? 0;
    const to = o.to ?? 100;
    const prog = interpolate(local, [4, 4 + fps * 1.1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
    const v = from + (to - from) * prog;
    const dec = o.decimals ?? 0;
    const num = v.toLocaleString('pt-BR', {minimumFractionDigits: dec, maximumFractionDigits: dec});
    const done = prog >= 1;
    return center(
      <div
        style={{
          textAlign: 'center',
          fontFamily: fontStack(st.font),
          fontWeight: 900,
          fontSize: o.size || 150,
          color: done ? accent : '#fff',
          letterSpacing: -3,
          transform: `scale(${p * (done ? 1 + 0.06 * Math.max(0, 1 - (local - 4 - fps * 1.1) / 8) : 1)})`,
          opacity: out,
          ...OUTLINE,
        }}
      >
        {o.prefix || ''}
        {num}
        {o.suffix || ''}
      </div>,
    );
  }

  if (o.type === 'stamp') {
    const s = interpolate(p, [0, 1], [2.4, 1]);
    return center(
      <div style={{textAlign: 'center', opacity: Math.min(1, p * 2) * out}}>
        <span
          style={{
            display: 'inline-block',
            padding: '14px 34px',
            border: `10px solid ${o.color || '#e63946'}`,
            color: o.color || '#e63946',
            borderRadius: 18,
            fontFamily: fontStack('Montserrat'),
            fontWeight: 900,
            fontSize: o.size || 96,
            letterSpacing: 4,
            textTransform: 'uppercase',
            transform: `rotate(${o.rot ?? -10}deg) scale(${s})`,
            background: 'rgba(255,255,255,0.88)',
            boxShadow: '0 18px 40px rgba(0,0,0,0.3)',
          }}
        >
          {o.text}
        </span>
      </div>,
    );
  }

  if (o.type === 'list') {
    const items = o.items || [];
    const per = Math.max(8, ((o.end - o.start) * fps * 0.7) / Math.max(1, items.length));
    return center(
      <div
        style={{
          background: 'rgba(255,255,255,0.95)',
          borderRadius: 32,
          padding: '30px 36px',
          boxShadow: '0 30px 70px rgba(0,0,0,0.4)',
          fontFamily: fontStack(st.font),
          color: '#111',
          transform: `scale(${p}) rotate(${(1 - p) * 4}deg)`,
          opacity: out,
        }}
      >
        {o.title ? <div style={{fontSize: 50, fontWeight: 900, marginBottom: 16}}>{o.title}</div> : null}
        {items.map((it, i) => {
          const ip = spring({frame: local - 6 - i * per, fps, config: {damping: 14, stiffness: 200}});
          return (
            <div key={i} style={{display: 'flex', alignItems: 'center', gap: 18, fontSize: 46, fontWeight: 700, margin: '12px 0', opacity: ip, transform: `translateX(${(1 - ip) * 60}px)`}}>
              <span style={{width: 50, height: 50, borderRadius: 14, background: accent, display: 'grid', placeItems: 'center', fontSize: 32, color: '#111', flex: 'none', transform: `scale(${ip})`}}>✓</span>
              {it}
            </div>
          );
        })}
      </div>,
      {width: Math.max(w, 0.8 * width), left: width * 0.1},
    );
  }

  if (o.type === 'headline') {
    const hlProg = interpolate(local, [8, 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    return center(
      <div
        style={{
          textAlign: 'center',
          fontFamily: fontStack(st.titleFont || st.font),
          fontWeight: 900,
          fontSize: o.size || 84,
          lineHeight: 1.08,
          color: '#fff',
          transform: `translateY(${(1 - p) * 30}px)`,
          opacity: Math.min(1, p * 1.5) * out,
          ...OUTLINE,
        }}
      >
        <Marked text={o.text || ''} hl={o.highlight} color={accent} prog={hlProg} />
      </div>,
      {width: width - 120, left: 60},
    );
  }
  return null;
};

export const Overlays: React.FC<{plan: Plan}> = ({plan}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  return (
    <>
      {(plan.overlays || [])
        .filter((o) => t >= o.start - 0.01 && t < o.end)
        .map((o, i) => (
          <OverlayItem key={`${o.type}-${o.start}-${i}`} plan={plan} o={o} />
        ))}
    </>
  );
};

// ---------------------------------------------------------------- CTA final
export const Cta: React.FC<{plan: Plan}> = ({plan}) => {
  const {width, height, durationInFrames} = useVideoConfig();
  const c = plan.cta;
  const {p, local, fps} = useLife(c?.start || 0, durationInFrames / 30 + 10, 160);
  if (!c || !c.text || local < 0) return null;
  const color = c.color || plan.style.ctaColor || plan.style.accent || '#ff3d6e';
  const pulse = 1 + 0.035 * Math.sin((local / fps) * Math.PI * 2.2);
  const arrowY = Math.abs(Math.sin((local / fps) * Math.PI * 2)) * 18;
  return (
    <div style={{position: 'absolute', left: 60, width: width - 120, top: height * (plan.style.ctaY ?? 0.62), textAlign: 'center', transform: `translateY(${(1 - p) * 80}px)`, opacity: Math.min(1, p * 1.5)}}>
      {c.sub ? (
        <div style={{fontFamily: fontStack(plan.style.font), fontWeight: 800, fontSize: 46, color: '#fff', marginBottom: 22, ...OUTLINE, WebkitTextStroke: '7px rgba(0,0,0,0.9)'}}>{c.sub}</div>
      ) : null}
      <div
        style={{
          display: 'inline-block',
          background: color,
          color: plan.style.ctaTextColor || '#fff',
          fontFamily: fontStack(plan.style.font),
          fontWeight: 900,
          fontSize: 58,
          padding: '26px 52px 30px',
          borderRadius: 999,
          boxShadow: `0 20px 50px rgba(0,0,0,0.45), 0 0 0 10px rgba(255,255,255,0.18)`,
          transform: `scale(${p * pulse})`,
        }}
      >
        {c.text}
      </div>
      <div style={{fontSize: 80, marginTop: 14, fontFamily: EMOJI_FONT, transform: `translateY(${arrowY}px)`}}>👇</div>
    </div>
  );
};

// ---------------------------------------------------------------- barra de progresso e grão
export const Progress: React.FC<{plan: Plan}> = ({plan}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, width} = useVideoConfig();
  if (!plan.style.progress) return null;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width, height: 10, background: 'rgba(255,255,255,0.18)'}}>
      <div style={{height: '100%', width: `${(frame / durationInFrames) * 100}%`, background: plan.style.accent || '#ffe14d', borderRadius: '0 6px 6px 0'}} />
    </div>
  );
};

export const Grain: React.FC<{plan: Plan}> = ({plan}) => {
  const frame = useCurrentFrame();
  const amt = plan.style.grain || 0;
  if (!amt) return null;
  const seed = Math.floor(frame / 2);
  const dx = Math.floor(random(`gx${seed}`) * 512);
  const dy = Math.floor(random(`gy${seed}`) * 512);
  return (
    <AbsoluteFill
      style={{
        opacity: amt * 1.6,
        mixBlendMode: 'overlay',
        backgroundImage: `url(${staticFile('fonts/grain.png')})`,
        backgroundRepeat: 'repeat',
        backgroundPosition: `${dx}px ${dy}px`,
      }}
    />
  );
};
