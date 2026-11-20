---
name: yap
description: "Template KLAP 'Yap elaborado': a pessoa em tela cheia falando (opinião, dica, storytime), com cortes secos e zoom alternado, uma palavra por vez grande ao lado do rosto e título em cima da cabeça. Use quando o usuário disser /yap, 'yap', 'só eu falando com legenda palavra por palavra', 'corte com zoom'. Precisa só do vídeo dele falando."
---

# /yap

Siga a skill **klap-base** (`~/.claude/skills/klap-base/SKILL.md`) do começo ao fim com `--template yap`.
O que é específico deste template:

- **Vídeos:** só o principal. Apoio é opcional: se vier, use em 1 ou 2 cenas `media` (tela cheia da mídia com a voz
  por baixo) nos momentos em que ela cita a coisa; o resto é ela.
- **Título:** em cima da cabeça nos primeiros ~3 s (o motor acha o rosto). Curto, até 6 palavras.
- **Cenas curtas** (1 a 2.6 s) com zoom alternado (`zoom` 1.0 / 1.16 / 1.04 / 1.24): o corte seco com mudança de zoom
  é o que dá ritmo. Nas frases de impacto use o zoom maior.
- **Legenda:** uma palavra por vez, grande, branca com contorno, ao lado do rosto (ou embaixo do queixo quando o
  rosto ocupa a tela toda). Palavras de 1 ou 2 letras podem ficar juntas com a próxima: junte em
  `captions[].words` se ficar piscando demais.
- **Animação (o forte do Yap):** palavras longas/números saem em amarelo e maiores, cada palavra entra girando um
  pouco. Use bastante elemento (1 a cada 3 a 5 s): `notif`, `search`, `stamp`, `list`, `counter`, `emoji`. Em close a
  pessoa desce sozinha quando o card entra. Título com marca-texto (`--highlight`). Exemplo pronto:
  `~/.claude/skills/klap-base/exemplos/planos/yap.json`.
- Ritmo é tudo: corte todos os respiros (`--gap 0.2` no cut se ainda sobrar pausa).
