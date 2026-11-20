---
name: telaverde
description: "Template KLAP 'Tela verde': a pessoa recortada na frente do vídeo que ela está comentando (react / opinião sobre post de outra pessoa), título forte no gancho e legenda orgânica em negrito. Use quando o usuário disser /telaverde, 'faz tela verde', 'eu comentando esse vídeo', 'me coloca na frente desse vídeo'. Precisa do vídeo dele falando + o(s) vídeo(s) comentado(s)."
---

# /telaverde

Siga a skill **klap-base** (`~/.claude/skills/klap-base/SKILL.md`) do começo ao fim com `--template telaverde`.
O que é específico deste template:

- **Vídeos:** principal = a pessoa falando; apoio = o vídeo (ou vídeos/prints) que ela está comentando. Sem vídeo de
  apoio não existe tela verde: peça antes de começar.
- **Passo 5 é obrigatório:** `$K matte "$P"` antes do autoplan.
- **Título:** o que o usuário escreveu depois do comando (ex.: `/telaverde quero que o título seja: ...`), exatamente.
  Fica nos primeiros ~3 s, em cima, com contorno.
- **Cenas:** a 1ª é ela em tela cheia com o título (o gancho). Depois alterna tela verde (ela na frente do vídeo
  comentado) com tela cheia a cada 2 ou 3 cenas. Cada tela verde mostra o trecho do vídeo comentado que bate com a
  fala: ache o segundo na folha (`build/mN_folha.jpg`) e ponha em `mediaStart`.
- **Recorte:** `cutoutScale` 0.75 a 0.85, embaixo e no centro; se o vídeo de fundo tem o rosto/assunto no centro,
  mova a pessoa para o lado (`cutoutX` 0.3 ou 0.7) pra não tampar.
- **Legenda:** frases curtas (até 4 palavras) brancas em negrito; a palavra falada ganha uma caixa amarela que pula.
- **Animação:** recorte com contorno branco de figurinha, transições slide/punch/zoom, barra de progresso, grão.
  Ponha `counter` nos números citados, `card` com print/foto do que está sendo comentado, `stamp` no veredito
  ("MITO", "ERRADO", "VERDADE"). Exemplo pronto: `~/.claude/skills/klap-base/exemplos/planos/telaverde.json`.
- Som do vídeo comentado: mudo por padrão; se ela quer que se ouça um trecho, `mediaVolume` 0.3 só naquela cena.
