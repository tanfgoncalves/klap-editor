import React from 'react';
import {AbsoluteFill, Img, interpolate, Loop, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {faceCenter, PUSH_FRAC, pushAt} from './common';
import {Plan, Scene} from './types';

type P = {plan: Plan; scene: Scene; startFrame: number};

// ---------------------------------------------------------------- mídia (imagem ou vídeo)
export const MediaFill: React.FC<{
  plan: Plan;
  mediaId?: string;
  mediaStart?: number;
  len: number;
  volume?: number;
  kenburns?: boolean;
  style?: React.CSSProperties;
  fit?: 'cover' | 'contain';
}> = ({plan, mediaId, mediaStart, len, volume, kenburns, style, fit}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const m = mediaId ? plan.media[mediaId] : undefined;
  const k = kenburns ? interpolate(frame, [0, Math.max(1, len)], [1.0, 1.07], {extrapolateRight: 'clamp'}) : 1;
  const fill: React.CSSProperties = {width: '100%', height: '100%', objectFit: fit || 'cover', transform: `scale(${k})`, ...style};
  if (!m) return <AbsoluteFill style={{background: '#151311'}} />;
  if (m.kind === 'image') return <Img src={staticFile(m.src)} style={fill} />;
  const start = Math.round((mediaStart || 0) * fps);
  const mdur = Math.max(1, Math.floor(m.dur * fps) - 1);
  const vol = volume || 0;
  if (start + len <= mdur) {
    return <OffthreadVideo src={staticFile(m.src)} trimBefore={start} muted={!vol} volume={vol} style={fill} />;
  }
  return (
    <Loop durationInFrames={mdur}>
      <OffthreadVideo src={staticFile(m.src)} muted={!vol} volume={vol} style={fill} />
    </Loop>
  );
};

const sceneLen = (scene: Scene, fps: number) => Math.max(1, Math.round((scene.end - scene.start) * fps));

// ---------------------------------------------------------------- pessoa
// desfoque barato: desenha a 1/10 do tamanho e amplia (o navegador suaviza)
export const CheapBlur: React.FC<{children: React.ReactNode; dim?: number; opacity?: number}> = ({children, dim = 0.6, opacity = 1}) => {
  const {width, height} = useVideoConfig();
  const k = 10;
  return (
    <AbsoluteFill style={{overflow: 'hidden', opacity}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: width / k, height: height / k, transform: `scale(${k * 1.15})`, transformOrigin: '0 0', marginLeft: -width * 0.075, marginTop: -height * 0.075, filter: `brightness(${dim}) saturate(1.2) blur(1.5px)`}}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

export const Speaker: React.FC<{plan: Plan; startFrame: number; style?: React.CSSProperties}> = ({plan, startFrame, style}) => (
  <OffthreadVideo
    src={staticFile(plan.speaker)}
    trimBefore={startFrame}
    muted
    style={{width: '100%', height: '100%', objectFit: 'cover', ...style}}
  />
);

const Vignette: React.FC<{strength?: number}> = ({strength = 0.35}) => (
  <AbsoluteFill
    style={{background: `radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 55%, rgba(0,0,0,${strength}) 100%)`}}
  />
);

export const FullLayout: React.FC<P> = ({plan, scene, startFrame}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {cx, cy} = faceCenter(plan);
  const len = sceneLen(scene, fps);
  const push = plan.style.kenburns ? interpolate(frame, [0, len], [1, 1.035], {extrapolateRight: 'clamp'}) : 1;
  const z = (scene.zoom || 1) * push;
  const {height} = useVideoConfig();
  const pv = pushAt(plan, scene.start + frame / fps);
  const dy = pv * PUSH_FRAC * height;
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      {pv > 0.001 ? (
        <CheapBlur dim={0.55} opacity={pv}>
          <Speaker plan={plan} startFrame={startFrame} />
        </CheapBlur>
      ) : null}
      <AbsoluteFill style={{transform: `translateY(${dy}px) scale(${1 - 0.06 * pv})`, transformOrigin: '50% 100%', borderRadius: 40 * pv, overflow: 'hidden', boxShadow: pv ? `0 -20px 60px rgba(0,0,0,${0.5 * pv})` : undefined}}>
        <Speaker plan={plan} startFrame={startFrame} style={{transform: `scale(${z})`, transformOrigin: `${cx * 100}% ${cy * 100}%`}} />
        {plan.style.vignette ? <Vignette strength={plan.style.vignette} /> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// mídia em cima (cartão arredondado sobre a própria mídia desfocada), você embaixo
export const SplitLayout: React.FC<P> = ({plan, scene, startFrame}) => {
  const {width, height, fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const len = sceneLen(scene, fps);
  const r = scene.splitRatio || 0.5;
  const topH = Math.round(height * r);
  const botH = height - topH;
  const {cy} = faceCenter(plan);
  const top = Math.min(0, Math.max(botH - height, botH * 0.4 - cy * height));
  const inset = plan.style.splitInset ?? 34;
  const enter = interpolate(frame, [0, 9], [0.92, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width, height: topH, overflow: 'hidden'}}>
        {inset ? (
          <>
            <CheapBlur dim={0.7}>
              <MediaFill plan={plan} mediaId={scene.media} mediaStart={scene.mediaStart} len={len} />
            </CheapBlur>
            <div
              style={{
                position: 'absolute',
                left: inset,
                top: inset,
                width: width - inset * 2,
                height: topH - inset * 2,
                borderRadius: 36,
                overflow: 'hidden',
                boxShadow: '0 24px 60px rgba(0,0,0,0.45)',
                border: '4px solid rgba(255,255,255,0.92)',
                transform: `scale(${enter})`,
              }}
            >
              <MediaFill plan={plan} mediaId={scene.media} mediaStart={scene.mediaStart} len={len} volume={scene.mediaVolume} kenburns={!!plan.style.kenburns} />
            </div>
          </>
        ) : (
          <MediaFill plan={plan} mediaId={scene.media} mediaStart={scene.mediaStart} len={len} volume={scene.mediaVolume} kenburns={!!plan.style.kenburns} />
        )}
      </div>
      <div style={{position: 'absolute', left: 0, top: topH, width, height: botH, overflow: 'hidden'}}>
        <div style={{position: 'absolute', left: 0, top, width, height}}>
          <Speaker plan={plan} startFrame={startFrame} />
        </div>
      </div>
      {!inset ? <div style={{position: 'absolute', left: 0, top: topH - 2, width, height: 4, background: 'rgba(255,255,255,0.9)'}} /> : null}
    </AbsoluteFill>
  );
};

// você recortado na frente do vídeo comentado, com contorno de figurinha
export const GreenLayout: React.FC<P> = ({plan, scene, startFrame}) => {
  const {width, height, fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const len = sceneLen(scene, fps);
  const s = scene.cutoutScale || plan.style.cutoutScale || 0.8;
  const x = scene.cutoutX ?? plan.style.cutoutX ?? 0.5;
  const dim = plan.style.bgDim || 0;
  const outline = plan.style.stickerOutline ?? true;
  const pop = interpolate(frame, [0, 8], [0.94, 1], {extrapolateRight: 'clamp'});
  // o contorno branco já vem pronto no cutout.webm (klap.py matte); aqui nada de filtro caro
  void outline;
  const filt = undefined;
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <MediaFill plan={plan} mediaId={scene.media} mediaStart={scene.mediaStart} len={len} volume={scene.mediaVolume} kenburns={!!plan.style.kenburns} />
      {dim ? <AbsoluteFill style={{background: `linear-gradient(180deg, rgba(0,0,0,${dim * 0.6}) 0%, rgba(0,0,0,${dim}) 70%, rgba(0,0,0,${dim * 2}) 100%)`}} /> : null}
      {plan.cutout ? (
        <div
          style={{
            position: 'absolute',
            width,
            height,
            left: (x - 0.5) * width,
            top: 0,
            transform: `scale(${s * pop})`,
            transformOrigin: '50% 100%',
            filter: filt,
          }}
        >
          <OffthreadVideo src={staticFile(plan.cutout)} trimBefore={startFrame} transparent muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const MediaLayout: React.FC<P> = ({plan, scene}) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <MediaFill plan={plan} mediaId={scene.media} mediaStart={scene.mediaStart} len={sceneLen(scene, fps)} volume={scene.mediaVolume} kenburns={!!plan.style.kenburns} />
      <Vignette strength={0.3} />
    </AbsoluteFill>
  );
};

export const WordCard: React.FC<P> = ({plan, scene}) => (
  <AbsoluteFill style={{background: scene.bg || plan.style.accent || '#111'}} />
);
