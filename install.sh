#!/usr/bin/env bash
# KLAP Editor: instala as skills no Claude Code (macOS).
#
#   ./install.sh            instala/atualiza (as skills viram links para esta pasta: `git pull` já atualiza)
#   ./install.sh --copy     copia as skills em vez de criar links
#   ./install.sh --check    só confere o que falta, não instala nada
#
# Variáveis opcionais:
#   CLAUDE_SKILLS_DIR    onde ficam as skills (padrão ~/.claude/skills)
#   KLAP_WHISPER_MODEL   um ggml-large-v3-turbo*.bin que você já tenha (pula o download de ~570 MB)
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
SKILLS_SRC="$REPO/skills"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
MOTOR="$SKILLS_SRC/klap-base/motor"
MODEL_DIR="$HOME/.cache/klap"
MODEL="$MODEL_DIR/ggml-large-v3-turbo-q5_0.bin"
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
MODE="link"
CHECK=0
for a in "$@"; do
  case "$a" in
    --copy) MODE="copy" ;;
    --check) CHECK=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $a"; exit 1 ;;
  esac
done

ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; }
info() { printf "\n\033[1m%s\033[0m\n" "$1"; }

info "1/6 Sistema"
if [ "$(uname)" != "Darwin" ]; then
  bad "O KLAP Editor precisa de macOS (usa o Vision da Apple para recortar a pessoa)."; exit 1
fi
ok "macOS $(sw_vers -productVersion) ($(uname -m))"

info "2/6 Ferramentas"
missing=()
need() { if command -v "$1" >/dev/null 2>&1; then ok "$1"; else bad "$1 (brew install $2)"; missing+=("$2"); fi; }
need ffmpeg ffmpeg
need ffprobe ffmpeg
need whisper-cli whisper-cpp
need yt-dlp yt-dlp
need node node
need npm node
need python3 python
if command -v swiftc >/dev/null 2>&1; then ok "swiftc"; else bad "swiftc (rode: xcode-select --install)"; fi
if command -v ffmpeg >/dev/null 2>&1 && ! ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libvpx-vp9; then
  bad "seu ffmpeg não tem libvpx-vp9 (precisa para o vídeo transparente da tela verde): brew reinstall ffmpeg"
fi
if [ ${#missing[@]} -gt 0 ]; then
  uniq=$(printf "%s\n" "${missing[@]}" | sort -u | tr '\n' ' ')
  echo
  echo "Falta instalar: $uniq"
  if [ $CHECK -eq 1 ]; then exit 1; fi
  if command -v brew >/dev/null 2>&1; then
    read -r -p "Instalar agora com o Homebrew? [s/N] " yn
    if [[ "$yn" =~ ^[sSyY] ]]; then brew install $uniq; else echo "Instale e rode de novo."; exit 1; fi
  else
    echo "Instale o Homebrew (https://brew.sh) e depois: brew install $uniq"; exit 1
  fi
fi
command -v swiftc >/dev/null 2>&1 || { echo "Instale as Command Line Tools: xcode-select --install"; exit 1; }
[ $CHECK -eq 1 ] && { echo; echo "Tudo certo com as ferramentas."; exit 0; }

info "3/6 Utilitário de recorte e rosto (Swift + Vision)"
mkdir -p "$MOTOR/bin"
swiftc -O "$MOTOR/klapvision.swift" -o "$MOTOR/bin/klapvision" 2> >(grep -v -E "warning|deprecated|^ *[0-9]+ \||^ *\||^\s*$|\^" >&2 || true)
ok "bin/klapvision compilado"

info "4/6 Remotion (motor de vídeo)"
( cd "$MOTOR/remotion" && npm install --no-audit --no-fund --loglevel=error )
( cd "$MOTOR/remotion" && npx --yes remotion browser ensure >/dev/null 2>&1 ) && ok "navegador do Remotion pronto" || ok "o navegador do Remotion baixa na primeira prévia"
ok "dependências instaladas"

info "5/6 Modelo do Whisper (transcrição em português)"
if [ -n "${KLAP_WHISPER_MODEL:-}" ] && [ -f "$KLAP_WHISPER_MODEL" ]; then
  mkdir -p "$MODEL_DIR"; ln -sf "$KLAP_WHISPER_MODEL" "$MODEL"; ok "usando $KLAP_WHISPER_MODEL"
elif [ -f "$MODEL" ]; then
  ok "já existe em $MODEL"
else
  mkdir -p "$MODEL_DIR"
  echo "  baixando ggml-large-v3-turbo-q5_0.bin (~570 MB, Hugging Face)..."
  curl -L --fail --progress-bar -o "$MODEL.part" "$MODEL_URL" && mv "$MODEL.part" "$MODEL"
  ok "salvo em $MODEL"
fi

info "6/6 Skills no Claude Code ($DEST)"
mkdir -p "$DEST"
stamp=$(date +%Y%m%d-%H%M%S)
for s in klap klap-base telaverde teladividida yap; do
  src="$SKILLS_SRC/$s"; dst="$DEST/$s"
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ] && [ "$MODE" = "link" ]; then ok "/$s (já ligado)"; continue; fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then mv "$dst" "$dst.bak-$stamp"; echo "  (a versão antiga de /$s foi guardada em $dst.bak-$stamp)"; fi
  if [ "$MODE" = "link" ]; then ln -s "$src" "$dst"; else cp -R "$src" "$dst"; fi
  ok "/$s"
done

echo
echo "Pronto! Abra o Claude Code e digite /klap (ou /yap, /telaverde, /teladividida, /klap-base)."
echo "Catálogo com os exemplos: open \"$SKILLS_SRC/klap-base/catalogo.html\""
echo "Os projetos ficam em ~/Movies/KLAP Editor/."
