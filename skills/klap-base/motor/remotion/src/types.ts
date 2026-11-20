export type Word = {w: string; s: number; e: number};
export type Caption = {start: number; end: number; words: Word[]; hide?: boolean};

export type Transition = 'cut' | 'punch' | 'flash' | 'slide' | 'zoomblur';

export type Scene = {
  id: number;
  start: number;
  end: number;
  layout: 'full' | 'split' | 'green' | 'media' | 'word' | 'card' | string;
  media?: string;
  mediaStart?: number;
  mediaVolume?: number;
  zoom?: number;
  keyword?: string;
  text?: string;
  captions?: boolean;
  cutoutScale?: number;
  cutoutX?: number;
  splitRatio?: number;
  bg?: string;
  transition?: Transition;
};

export type Media = {src: string; kind: 'video' | 'image'; dur: number; name?: string; credit?: string};

export type Overlay = {
  type: 'emoji' | 'card' | 'notif' | 'search' | 'counter' | 'stamp' | 'list' | 'headline' | string;
  start: number;
  end: number;
  x?: number; // centro, 0..1
  y?: number; // centro, 0..1
  w?: number; // largura, 0..1
  rot?: number;
  size?: number;
  // conteúdo por tipo
  emoji?: string;
  media?: string;
  label?: string;
  app?: string;
  icon?: string;
  title?: string;
  text?: string;
  from?: number;
  to?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  items?: string[];
  color?: string;
  highlight?: string;
  push?: boolean;
};

export type Sfx = {t: number; name: string; volume?: number};

export type Plan = {
  template: string;
  fps: number;
  width: number;
  height: number;
  duration: number;
  speaker: string;
  cutout: string | null;
  face: {x: number; y: number; w: number; h: number} | null;
  title: {text: string; start: number; end: number; highlight?: string};
  style: Record<string, any>;
  media: Record<string, Media>;
  scenes: Scene[];
  captions: Caption[];
  overlays?: Overlay[];
  sfx?: Sfx[];
  cta?: {text: string; sub?: string; start: number; color?: string} | null;
  music: {src: string; volume?: number; duck?: number} | null;
};
