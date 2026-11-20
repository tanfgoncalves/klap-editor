import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Captions} from './captions';
import {useFonts} from './common';
import {FullLayout, GreenLayout, MediaLayout, SplitLayout, WordCard} from './layouts';
import {Cta, Grain, Keyword, Overlays, Progress, Title} from './overlays';
import {Plan, Scene} from './types';

export type {Plan} from './types';

// transição de entrada da cena (os primeiros quadros)
const SceneShell: React.FC<{scene: Scene; children: React.ReactNode}> = ({scene, children}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  const tr = scene.transition || 'cut';
  const ease = Easing.out(Easing.cubic);
  let style: React.CSSProperties = {};
  let flash = 0;
  if (tr === 'punch') {
    const s = interpolate(frame, [0, 7], [1.14, 1], {extrapolateRight: 'clamp', easing: ease});
    const b = interpolate(frame, [0, 5], [6, 0], {extrapolateRight: 'clamp'});
    style = {transform: `scale(${s})`, filter: b > 0.1 ? `blur(${b}px)` : undefined};
  } else if (tr === 'zoomblur') {
    const s = interpolate(frame, [0, 9], [1.32, 1], {extrapolateRight: 'clamp', easing: ease});
    const b = interpolate(frame, [0, 7], [16, 0], {extrapolateRight: 'clamp'});
    style = {transform: `scale(${s})`, filter: b > 0.1 ? `blur(${b}px)` : undefined};
  } else if (tr === 'slide') {
    const x = interpolate(frame, [0, 8], [width * 0.55, 0], {extrapolateRight: 'clamp', easing: ease});
    const b = interpolate(frame, [0, 6], [14, 0], {extrapolateRight: 'clamp'});
    style = {transform: `translateX(${x}px)`, filter: b > 0.1 ? `blur(${b}px)` : undefined};
  } else if (tr === 'flash') {
    flash = interpolate(frame, [0, 5], [0.85, 0], {extrapolateRight: 'clamp'});
  }
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <AbsoluteFill style={style}>{children}</AbsoluteFill>
      {flash > 0 ? <AbsoluteFill style={{background: '#fff', opacity: flash}} /> : null}
    </AbsoluteFill>
  );
};

export const Reel: React.FC<Plan> = (plan) => {
  useFonts();
  const {fps} = useVideoConfig();
  const words = plan.captions.flatMap((c) => c.words);
  const speaking = (f: number) => {
    const t = f / fps;
    return words.some((w) => t >= w.s - 0.15 && t <= w.e + 0.25);
  };
  const mv = plan.music?.volume ?? 0.12;
  const duck = plan.music?.duck ?? 0.35;
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Audio src={staticFile(plan.speaker)} />
      {plan.music ? (
        <Audio
          src={staticFile(plan.music.src)}
          loop
          volume={(f) => {
            const fadeIn = Math.min(1, f / (fps * 0.8));
            return mv * fadeIn * (speaking(f) ? duck : 1);
          }}
        />
      ) : null}
      {(plan.sfx || []).map((s, i) => (
        <Sequence key={`sfx${i}`} from={Math.max(0, Math.round(s.t * fps))} durationInFrames={fps * 2} name={`som ${s.name}`}>
          <Audio src={staticFile(`sfx/${s.name}.wav`)} volume={s.volume ?? 0.3} />
        </Sequence>
      ))}
      {plan.scenes.map((s) => {
        const from = Math.round(s.start * fps);
        const dur = Math.max(1, Math.round(s.end * fps) - from);
        let body: React.ReactNode;
        if (s.layout === 'split') body = <SplitLayout plan={plan} scene={s} startFrame={from} />;
        else if (s.layout === 'green') body = <GreenLayout plan={plan} scene={s} startFrame={from} />;
        else if (s.layout === 'media') body = <MediaLayout plan={plan} scene={s} startFrame={from} />;
        else if (s.layout === 'word') body = <WordCard plan={plan} scene={s} startFrame={from} />;
        else body = <FullLayout plan={plan} scene={s} startFrame={from} />;
        return (
          <Sequence key={s.id} from={from} durationInFrames={dur} name={`cena ${s.id} ${s.layout}`}>
            <SceneShell scene={s}>{body}</SceneShell>
            <Keyword plan={plan} scene={s} />
          </Sequence>
        );
      })}
      <Grain plan={plan} />
      <Overlays plan={plan} />
      <Captions plan={plan} />
      <Title plan={plan} />
      <Cta plan={plan} />
      <Progress plan={plan} />
    </AbsoluteFill>
  );
};
