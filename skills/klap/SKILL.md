---
name: klap
description: "Menu do KLAP Editor (editor de reels por template). Mostra os modelos (Imparável, Tela verde, Tela dividida, Yap), pede o vídeo bruto, edita tudo sozinho (corta pausas e erros, acelera, legenda animada, efeitos, sons, elementos animados, busca imagens/vídeos/música livres na internet quando faltar) e entrega prévia + storyboard pra aprovar. Também escreve o roteiro por nicho quando ainda não há vídeo. Use quando o usuário disser /klap, 'abre o editor', 'quero editar um vídeo', 'qual modelo uso', 'faz um roteiro pra gravar'."
---

# /klap: o menu do editor

Tudo roda aqui no Claude, no Mac do usuário. Ele escolhe, manda o vídeo, você faz o resto e só para nos pontos de
aprovação. Fale em português simples.

## 1. Escolher o modelo
Se ele já disse o modelo (ou usou /telaverde, /teladividida, /yap, /klap-base), pule. Senão pergunte com
AskUserQuestion (uma pergunta, 4 opções):
- **Yap elaborado**: você falando em tela cheia, zoom, palavra por palavra, cards animados.
- **Tela verde**: você recortado na frente do vídeo que está comentando.
- **Tela dividida**: imagem em cima, você embaixo, palavras-chave grandes.
- **Imparável**: só o corte limpo (pausas, erros, 1.2x, áudio).
Pergunte também, se fizer sentido no mesmo card: título do gancho e o CTA final (ex.: "Comenta EU QUERO").
O catálogo visual fica em `~/.claude/skills/klap-base/catalogo.html` (`open` nele se ele quiser ver os exemplos).

## 2. Pedir o vídeo
"Arrasta aqui o vídeo bruto (e o vídeo/imagens de apoio, se tiver)." Espere. Se ele disser que ainda não gravou,
ofereça o roteiro: pergunte o nicho e siga `~/.claude/skills/klap-base/roteiros.md` (roteiro + 3 ganchos + dicas
de gravação). Depois espere o vídeo.
Tela verde sem vídeo comentado (fala de conselho/opinião): ofereça fundos ilustrativos por tema (stock) em vez de
recusar. Se ele mandar um link (YouTube, Drive) em vez de arquivo: YouTube via `yt-dlp` (só o trecho necessário); Instagram
não (precisa de login, peça o arquivo).

## 3. Editar
Siga a skill do modelo escolhido (`~/.claude/skills/<modelo>/SKILL.md`), que segue a base
`~/.claude/skills/klap-base/SKILL.md`. Faça tudo sem perguntar: cortes, recorte, plano, elementos, sons.
Quando faltar mídia de apoio, **busque você mesmo**:
1. o que ele mandou; 2. `klap.py buscar --tipo stock` (vídeos Mixkit) e `buscar` (imagens Openverse/Wikimedia, licença livre, crédito automático em
`creditos.txt`); 3. YouTube Creative Commons (`--tipo youtube --trecho`); 4. imagem gerada no Higgsfield (gasta
créditos dele: pergunte antes, numa linha). Música: `klap.py buscar "<clima>" --tipo musica` (sem "ND").
Para entender uma referência que ele mandar (outro reel), assista com a skill `watch` ou extraia quadros com ffmpeg
e copie a estrutura, nunca o conteúdo.

## 4. Aprovar e entregar
Prévia + storyboard abertos no Mac → espere "pode fazer" → `klap.py render` → diga o caminho do arquivo final e,
se houver, lembre dos créditos de `creditos.txt` (cole na legenda do post quando a licença pedir atribuição).
