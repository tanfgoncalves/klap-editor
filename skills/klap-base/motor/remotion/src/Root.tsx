import React from 'react';
import {Composition} from 'remotion';
import {Reel, Plan} from './Reel';

const exemplo: Plan = {
  template: 'yap',
  fps: 30,
  width: 1080,
  height: 1920,
  duration: 3,
  speaker: 'assets/cut.mp4',
  cutout: null,
  face: {x: 0.35, y: 0.2, w: 0.3, h: 0.18},
  title: {text: '', start: 0, end: 0},
  style: {},
  media: {},
  scenes: [{id: 1, start: 0, end: 3, layout: 'full'}],
  captions: [],
  music: null,
};

export const Root: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel as any}
    defaultProps={exemplo as any}
    durationInFrames={90}
    fps={30}
    width={1080}
    height={1920}
    calculateMetadata={({props}: any) => ({
      durationInFrames: Math.max(1, Math.round(props.duration * props.fps)),
      fps: props.fps,
      width: props.width,
      height: props.height,
    })}
  />
);
