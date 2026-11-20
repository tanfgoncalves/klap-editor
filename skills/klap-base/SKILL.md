---
name: klap-base
description: "KLAP Editor, a base de todos os templates de reels. Pega um vídeo bruto falando pra câmera (com pausas e erros), corta pausas e erros, acelera 1.2x sem mudar a voz, limpa o áudio, enquadra no rosto e, com um template (/telaverde, /teladividida, /yap), monta o reel 1080x1920 com legenda animada, título com marca-texto, transições, efeitos sonoros, emojis, cards animados (notificação, busca, contador, carimbo, lista, foto), música com abaixamento na fala e CTA final; busca mídia livre na internet quando falta; abre storyboard + prévia pra aprovar e só renderiza depois do 'pode fazer'. Use quando o usuário disser /klap-base, 'corta as pausas desse vídeo', 'deixa imparável', 'edita esse vídeo no template X', ou quando /klap ou um template KLAP chamar esta base. Sozinha (sem template) entrega só o corte limpo."
---

# KLAP Editor (base)

Motor: `~/.claude/skills/klap-base/motor/` (abaixo `$K` = `python3 ~/.claude/skills/klap-base/motor/klap.py`).
Projetos: um por vídeo em `~/Movies/KLAP Editor/AAAA-MM-DD <nome curto>/` (abaixo `$P`, sempre entre aspas).
Exemplos prontos (bons modelos de plan.json): `~/.claude/skills/klap-base/exemplos/planos/{yap,telaverde,teladividida}.json`. Roteiros por nicho: `~/.claude/skills/klap-base/roteiros.md`.
Fale com o usuário em português simples. Se ele ditar por voz, entenda pelo contexto.

## O fluxo (mostre este checklist e vá marcando)
1. Ler a skill do template (se houver) e esta base
2. Achar os vídeos (principal + apoio)
3. Transcrever a fala
4. Cortes: pausas fora, erros fora, 1.2x, áudio limpo
5. Recortar a pessoa do fundo (só se o template pedir)
6. Plano: título, cenas, legendas, mídias no lugar certo
7. Animação: elementos, emojis, sons, música, CTA
8. Storyboard + prévia (abertos no Mac)
9. Render final (só depois da aprovação)

### 1-2. Vídeos
O usuário arrasta os arquivos no chat ou diz onde estão. Sem caminho, procure os mais recentes:
`ls -t ~/Downloads/*.{mov,MOV,mp4,MP4} 2>/dev/null | head`. O **principal** é a pessoa falando pra câmera;
os outros são **apoio** (vídeo comentado, imagens, B-roll). Se não der pra saber qual é qual, pergunte numa linha.

### 3. Preparar e transcrever
```bash
$K prep "$P" <principal> [apoio1 apoio2 ...]
```
Vídeo deitado (16:9) é cortado em 9:16 centralizado no rosto sozinho. Imprime a transcrição com tempos originais e
gera `build/mN_folha.jpg` (6 quadros de cada vídeo de apoio). **Olhe cada folha** (Read) para saber o que cada mídia
mostra e em que segundo. Mais mídias depois: `$K media "$P" arquivo...`.

### 4. Cortes
Leia a transcrição. Ache erros e retakes: frase começada e repetida, "não, peraí", "de novo", gaguejo longo, e o
"se inscreve no canal" que não serve no reel. Fique com a ÚLTIMA versão boa de cada frase e corte o resto com
`--drop` (tempos ORIGINAIS, `ini-fim,ini-fim`).
```bash
$K cut "$P" --speed 1.2 [--drop "3.10-6.80,12.0-13.4"]
```
Pausas saem sozinhas. `--speed 1.0` se ele pedir sem acelerar. Confira a transcrição editada que o comando imprime.
Sem template (só `/klap-base`): copie `assets/cut.mp4` para `final/` e pare aqui.

### 5. Recorte (tela verde)
`$K matte "$P"`: Vision da Apple, no Mac (~30 s para 30 s de vídeo). Gera `assets/cutout.webm` transparente.

### 6. Plano
```bash
$K autoplan "$P" --template <telaverde|teladividida|yap> --title "<título>" [--highlight "<trecho do título>"] \
   [--cta "Comenta EU QUERO" --cta-sub "Quer o material?"]
```
Cria `plan.json` (o estado do vídeo) com cenas, transições, legendas, emojis e sons automáticos. **Depois refine
você mesmo** editando o plan.json:
- Cenas pelo sentido: quebre onde a ideia muda, 1 a 3.5 s. Sem buraco: `start` de uma = `end` da anterior.
- Mídia certa na hora certa: quando a fala cita algo que aparece numa mídia, ponha essa mídia na cena e
  `mediaStart` no segundo certo (use a folha).
- Título: o texto que o usuário pediu, exatamente. `highlight` = 1 a 3 palavras do título com marca-texto.
- Legendas: corrija nomes e palavras erradas em `captions[].words[].w` (nunca invente fala).
- Palavra-chave (`keyword`): 1 ou 2 palavras fortes, só onde o template usa.

### 7. Animação (é o que deixa o vídeo vivo; faça em todo vídeo)
Leia a transcrição editada e coloque **1 elemento a cada 3 a 6 s**, sempre no segundo em que a palavra é dita
(pegue o tempo em `captions[].words[].s`). Tipos em `overlays[]`:
| tipo | quando usar | campos |
|---|---|---|
| `emoji` | emoção ou objeto citado (o autoplan já põe alguns) | `emoji`, `x`, `y`, `size` (230) |
| `notif` | "recebi uma mensagem", cliente, venda, seguidor | `app`, `icon` (emoji), `title`, `text` |
| `search` | "pesquisa", "procura no Google", termo a buscar | `text` (digita sozinho) |
| `counter` | número, preço, porcentagem | `from`, `to`, `prefix` ("R$ "), `suffix` ("%"), `decimals` |
| `stamp` | erro, mito, verdade, proibido, palavra de impacto | `text`, `color`, `rot` |
| `list` | 2 a 4 pontos, passos, dicas | `title`, `items` |
| `card` | foto/print/vídeo de apoio flutuando | `media` (id), `label`, `rot`, `w` |
| `headline` | frase de impacto escrita com marca-texto | `text`, `highlight` |
Todos têm `start`, `end` (s de edição), e `x`, `y` (centro, 0 a 1), `w` (largura 0 a 1). Em close (rosto alto), os
tipos grandes (card, list, search, counter, stamp, headline) fazem a pessoa descer com fundo desfocado sozinhos;
deixe `y` entre 0.15 e 0.25. Regras: dois elementos grandes nunca ao mesmo tempo (o sync acusa), nada nos
primeiros 3 s além do título, emoji no máximo 1 a cada 4 s, `notif` sempre em cima (`y` 0.05).
Outros controles: `scenes[].transition` (`cut`, `punch`, `slide`, `zoomblur`, `flash`; use `slide`/`zoomblur` em
troca de assunto, `punch` em frase de impacto, `cut` no resto), `cta` (últimos ~2.5 s), música:
`$K buscar "$P" "<clima em inglês: upbeat, lofi, cinematic>" --tipo musica` e depois `--pegar N`.
Depois de editar: `$K sync "$P"` (refaz os sons automáticos e confere o plano). Som manual:
`{"t": 4.2, "name": "pop|whoosh|hit|ding|click|riser|type|notif", "volume": 0.3, "manual": true}` em `sfx[]`.

### Buscar mídia na internet (quando falta apoio)
```bash
$K buscar "$P" <categoria> --tipo stock                                       # VÍDEOS de banco (Mixkit, licença livre):
                                       # 1 palavra em inglês (office, phone, friends, rain, sunrise, clock, city, money...)
                                       # gera build/busca_stock.jpg com miniaturas: OLHE antes de escolher
$K buscar "$P" "<termo em inglês>" --tipo imagem|video|musica|som|youtube      # lista resultados
$K buscar "$P" "<termo>" --tipo imagem --pegar 2                              # baixa e vira mídia mN
$K buscar "$P" "<termo>" --tipo youtube --pegar 0 --trecho 10-25              # trecho de vídeo CC do YouTube
```
Para fundo de tela verde e tela dividida prefira `stock` (vídeo bonito, moderno); `imagem` do Openverse é fraca
para conceitos (use 1 palavra). Só licenças livres (Mixkit 4K, CC0, domínio público, CC BY, CC BY-SA); o crédito vai para `$P/creditos.txt`. Olhe a folha da
mídia antes de usar. Imagem gerada com IA (Higgsfield) só com o ok dele (gasta créditos).

### 8. Prévia e storyboard
```bash
$K preview "$P"               # prévia leve (540x960) + storyboard.html, abre no Mac
$K preview "$P" --seconds 8   # só o começo, para vídeo longo
```
Antes de mandar, olhe você mesmo os quadros-chave:
`ffmpeg -v error -y -i "$P/build/previa.mp4" -vf "fps=1/1.2,scale=216:-2,tile=8x2" -frames:v 1 "$P/build/folha_previa.jpg"`
(ou quadros nos segundos exatos de cada elemento com `-ss`). Confira: algo sobre o rosto, texto cortado, dois
elementos brigando, mídia errada. Corrija e refaça. Depois diga que o storyboard e a prévia estão abertos e espere.

### Alterações
Ele fala por cena ("cena 9 troca o fundo por uma imagem X", "legenda maior", "tira o emoji"). Edite plan.json,
`sync`, `preview` de novo. Imagem nova: `$K media "$P" arquivo` ou `buscar`.

### 9. Final (só depois do "pode fazer")
`$K render "$P" [--name "nome do arquivo"]` → `final/<nome>.mp4` (1080x1920 H.264), mostra no Finder.
Diga o caminho, a duração e, se `creditos.txt` existir, que os créditos vão na legenda do post.

## plan.json: outros campos
| campo | o que faz |
|---|---|
| `scenes[].layout` | `full`, `split` (mídia em cima), `green` (recortado na frente da mídia), `media` (só a mídia), `word` (cartão colorido) |
| `scenes[].media`, `mediaStart`, `mediaVolume` | mídia da cena, de que segundo começa, volume do som dela (padrão 0) |
| `scenes[].zoom` | 1.0 normal, 1.15 aproxima no rosto |
| `scenes[].captions` | `false` esconde a legenda na cena |
| `scenes[].cutoutScale`, `cutoutX`, `splitRatio` | recorte (tamanho, posição) e altura da parte de cima no split |
| `captions[]` | `{start, end, words:[{w,s,e}]}`; `hide: true` esconde uma |
| `style.captionSize`, `captionY`, `accent`, `captionAnim` | tamanho (px em 1080), altura (até 0.75), cor de destaque, animação (`box`, `fill`, `pill`, `word`) |
| `style.titleSize`, `titleY`, `titleStyle` | `outline`, `card` ou `above-head` |
| `style.progress`, `grain`, `vignette`, `stickerOutline`, `bgDim`, `sfxVolume` | barra de progresso, grão, vinheta, contorno branco no recorte, escurecer fundo, volume geral dos sons |
| `music` | `{"src": "assets/media/musica.mp3", "volume": 0.12, "duck": 0.35}` (abaixa sozinha quando há fala) |
| `cta` | `{"text", "sub", "start", "color"}` botão final pulsando com seta |

## Regras
- Nunca coloque na tela algo que a pessoa não falou (fora o título e o CTA que o usuário pediu).
- O rosto nunca fica coberto.
- Nada renderiza em qualidade final antes do "pode fazer".
- Vídeo de terceiros comentado na tela verde é responsabilidade dele; em YouTube, avise sobre direito autoral.
- Erro de ferramenta: diga o que faltou e o comando para resolver. Instalação/consertos: rode de novo o `install.sh` do
  repositório (ele confere ffmpeg, whisper-cpp, yt-dlp, Node, o modelo do Whisper e o Remotion).
