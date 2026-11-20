---
name: teladividida
description: "Template KLAP 'Tela dividida elegante': imagem ou vídeo em cima e a pessoa embaixo, alternando com ela em tela cheia e palavras-chave grandes em serifa itálica, legenda em pílula branca na divisão. Use quando o usuário disser /teladividida, 'tela dividida', 'imagem em cima e eu embaixo', 'split'. Precisa do vídeo dele falando + imagens ou vídeos de apoio."
---

# /teladividida

Siga a skill **klap-base** (`~/.claude/skills/klap-base/SKILL.md`) do começo ao fim com `--template teladividida`.
O que é específico deste template:

- **Vídeos:** principal = a pessoa falando; apoio = imagens, prints ou vídeos que ilustram o que ela diz (antes e
  depois, produto, notícia, print de post). Sem apoio, sugira usar /yap ou pergunte o que mostrar.
- **Título:** caixa na cor de destaque (`style.accent`, padrão vinho #b3123a) com serifa itálica, nos primeiros ~3 s.
  Se o usuário der a cor do CTA/marca, troque `style.accent`.
- **Cenas:** 1ª em tela cheia com o título. Depois alterna `split` (mídia em cima que mostra o que está sendo dito)
  com `full` + `keyword` (a palavra mais forte da cena, grande, em cima). Mais split que full (uns 60/40).
- **Mídia certa:** cada split mostra a mídia que casa com a fala daquela cena; varie, não repita a mesma mídia
  em seguida a não ser que seja a continuação do mesmo assunto.
- **Legenda:** pílula branca com texto escuro e a palavra falada na cor de destaque; na tela dividida fica na linha
  da divisão, na tela cheia fica embaixo.
- **Animação:** a mídia de cima fica num cartão arredondado com borda sobre ela mesma desfocada; a palavra-chave
  entra letra por letra com traço na cor de destaque, acima da cabeça. Transições slide/flash, emoji no canto.
  Exemplo pronto: `~/.claude/skills/klap-base/exemplos/planos/teladividida.json`.
- Rosto no painel de baixo: o motor centraliza pelo rosto; se cortar a cabeça, mude `splitRatio` (0.45).
