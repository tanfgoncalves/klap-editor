#!/usr/bin/env python3
"""KLAP Editor: motor de edição de reels por template.

Fluxo (uma pasta de projeto por vídeo):
  klap.py prep     <projeto> <principal> [extras...]   prepara, transcreve, folha de cada extra
  klap.py cut      <projeto> [--speed 1.2] [--drop a-b,c-d] [--gap 0.25]
                                                       corta pausas/erros, acelera sem mudar a voz, limpa o áudio
  klap.py matte    <projeto>                           recorta a pessoa do fundo (tela verde)
  klap.py autoplan <projeto> --template X [--title "..."] [--force]
                                                       plano inicial (cenas, legendas, mídias) em plan.json
  klap.py sync     <projeto>                           depois de editar o plan.json: refaz sons e confere
  klap.py buscar   <projeto> "termo" --tipo imagem|stock|video|musica|som|youtube [--pegar N] [--trecho 10-25]
                                                       mídia livre (Openverse, Wikimedia, YouTube CC) com crédito
  klap.py preview  <projeto> [--seconds 8]             prévia leve + storyboard cena por cena (abre no Mac)
  klap.py render   <projeto> [--name "..."]            vídeo final 1080x1920 (só depois da aprovação)
  klap.py status   <projeto>                           o que já foi feito

Tempos: "originais" = no vídeo bruto; "de edição" = no vídeo cortado e acelerado (plan.json usa estes).
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parent
SKILL = MOTOR.parent
REMOTION = MOTOR / "remotion"
VISION = MOTOR / "bin" / "klapvision"
TEMPLATES = MOTOR / "templates"
FONTS = MOTOR / "fonts"
WHISPER_MODELS = [p for p in [
    Path(os.environ["KLAP_WHISPER_MODEL"]) if os.environ.get("KLAP_WHISPER_MODEL") else None,
    Path.home() / ".cache/klap/ggml-large-v3-turbo-q5_0.bin",
] if p]
FPS = 30
W, H = 1080, 1920
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

STOP = set("""a o as os um uma uns umas de do da dos das no na nos nas em por pra para pro com sem que se
e ou mas mais muito muita isso esse essa este esta isto aquele aquela ele ela eles elas eu voce você vc
me te lhe nos vos meu minha seu sua teu tua é e foi ser ter tem tá ta to tô estou está esta são sao
já ja não nao sim só so tambem também como quando onde porque porquê quem qual aqui ali lá la então
entao assim tipo né ne aí ai ok gente coisa vai vou""".split())


def run(cmd, **kw):
    r = subprocess.run(cmd, text=True, capture_output=True, **kw)
    if r.returncode != 0:
        sys.stderr.write(r.stdout[-3000:] + "\n" + r.stderr[-3000:] + "\n")
        sys.exit(f"falhou: {' '.join(map(str, cmd[:4]))} ...")
    return r


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
             "-of", "json", str(path)])
    j = json.loads(r.stdout)
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    a = any(s.get("codec_type") == "audio" for s in j.get("streams", []))
    return {"dur": float(j.get("format", {}).get("duration", 0) or 0), "w": v.get("width"), "h": v.get("height"),
            "audio": a}


def load(p):
    return json.loads(Path(p).read_text())


def save(p, data):
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def proj(path):
    P = Path(path).expanduser().resolve()
    return P


def state(P):
    f = P / "build" / "project.json"
    return load(f) if f.exists() else {}


def save_state(P, st):
    f = P / "build" / "project.json"
    if f.exists():
        disk = load(f)
        have = {m["id"] for m in st.get("media", [])}
        extra = [m for m in disk.get("media", []) if m["id"] not in have]
        if extra:
            st["media"] = sorted(st.get("media", []) + extra, key=lambda m: int(m["id"][1:]))
        for k in ("music", "cutout"):
            if disk.get(k) and not st.get(k):
                st[k] = disk[k]
    save(f, st)


def next_media_id(P, st):
    used = {m["id"] for m in st.get("media", [])} | {f.stem for f in (P / "assets" / "media").glob("m*.*")}
    n = 1
    while f"m{n}" in used:
        n += 1
    return f"m{n}"


# ---------------------------------------------------------------- transcrição
def whisper_model():
    for m in WHISPER_MODELS:
        if m.exists():
            return m
    sys.exit("modelo do Whisper não encontrado. Rode o install.sh do KLAP Editor (baixa para ~/.cache/klap) "
             "ou aponte KLAP_WHISPER_MODEL para um ggml-large-v3-turbo*.bin")


def transcribe(wav, out_base):
    model = whisper_model()
    run(["whisper-cli", "-m", str(model), "-l", "pt", "-ml", "1", "-sow", "-oj", "-np",
         "-t", str(max(4, (os.cpu_count() or 8) - 2)), "-dtw", "large.v3.turbo", "-of", str(out_base), "-f", str(wav)])
    j = load(str(out_base) + ".json")
    words = []
    for seg in j.get("transcription", []):
        t = seg.get("text", "")
        if not t.strip():
            continue
        s = seg["offsets"]["from"] / 1000.0
        e = seg["offsets"]["to"] / 1000.0
        w = t.strip()
        # whisper.cpp às vezes separa a pontuação num "segmento" próprio
        if words and re.fullmatch(r"[\.,!?;:…]+", w):
            words[-1]["w"] += w
            continue
        if words and not t.startswith(" ") and words[-1]["e"] >= s - 0.02:
            words[-1]["w"] += w  # pedaço da mesma palavra
            words[-1]["e"] = e
            continue
        words.append({"w": w, "s": round(s, 3), "e": round(max(e, s + 0.05), 3)})
    return words


def silences(path, noise="-35dB", d=0.2):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                        f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"], text=True, capture_output=True)
    out, cur = [], None
    for line in r.stderr.splitlines():
        m = re.search(r"silence_start: ([\d\.\-e]+)", line)
        if m:
            cur = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d\.e]+)", line)
        if m and cur is not None:
            out.append([round(cur, 3), round(float(m.group(1)), 3)])
            cur = None
    if cur is not None:
        out.append([round(cur, 3), round(probe(path)["dur"], 3)])
    return out


def transcript_lines(words, gap=0.45):
    lines, cur = [], []
    for i, w in enumerate(words):
        if cur and (w["s"] - words[i - 1]["e"] > gap or re.search(r"[\.!?]$", words[i - 1]["w"])):
            lines.append(cur)
            cur = []
        cur.append(i)
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        a, b = words[ln[0]], words[ln[-1]]
        out.append(f"[{ln[0]:>3}-{ln[-1]:<3}] {a['s']:6.2f}-{b['e']:6.2f}  " + " ".join(words[i]["w"] for i in ln))
    return "\n".join(out)


# ---------------------------------------------------------------- prep
def cmd_prep(a):
    P = proj(a.projeto)
    for d in ["assets/media", "build", "fonts", "final"]:
        (P / d).mkdir(parents=True, exist_ok=True)
    for f in FONTS.glob("*.woff2"):
        shutil.copy2(f, P / "fonts" / f.name)
    main = Path(a.principal).expanduser().resolve()
    if not main.exists():
        sys.exit(f"não achei o vídeo principal: {main}")
    raw = P / "assets" / "raw.mp4"
    print(f"preparando {main.name} -> 1080x1920 30fps")
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p"
    norm = P / "build" / "src_norm.mp4"
    # normaliza (gira certo, até 1920 de altura) para medir a proporção e achar o rosto
    run(["ffmpeg", "-v", "error", "-y", "-i", str(main), "-vf", "scale=-2:'min(1920,ih)',format=yuv420p", "-an",
         "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-t", "120", str(norm)])
    ni = probe(norm)
    if ni["w"] and ni["h"] and ni["w"] / ni["h"] > 0.62:
        # vídeo deitado: corta 9:16 centralizado no rosto
        fj = P / "build" / "face_src.json"
        run([str(VISION), "face", str(norm), str(fj), "1.0"])
        fm = load(fj)["median"]
        cx = fm["x"] + fm["w"] / 2
        cw = ni["h"] * 9 / 16 / ni["w"]  # largura do corte em fração
        x0 = min(max(cx - cw / 2, 0.0), 1.0 - cw)
        vf = (f"crop=iw*{cw:.5f}:ih:iw*{x0:.5f}:0,scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},fps={FPS},format=yuv420p")
        print(f"vídeo deitado: enquadrando no rosto (centro x={cx:.2f})")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(main), "-vf", vf,
         "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", str(raw)])
    norm.unlink(missing_ok=True)
    wav = P / "build" / "raw16k.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    print("transcrevendo (Whisper turbo, pt)...")
    words = transcribe(wav, P / "build" / "whisper_raw")
    rdur = probe(raw)["dur"]
    for w in words:  # o whisper às vezes passa do fim do áudio
        w["e"] = round(min(w["e"], rdur), 3)
        w["s"] = round(min(w["s"], w["e"] - 0.05), 3)
    sil = silences(raw)
    media = []
    for i, e in enumerate(a.extras or [], 1):
        media.append(add_media(P, Path(e).expanduser().resolve(), f"m{i}"))
    st = {"source": str(main), "raw": "assets/raw.mp4", "rawDur": probe(raw)["dur"], "wordsRaw": words,
          "silences": sil, "media": media}
    save_state(P, st)
    (P / "build" / "transcricao_original.txt").write_text(transcript_lines(words))
    print("\nTRANSCRIÇÃO (tempos originais, [índices das palavras]):")
    print(transcript_lines(words))
    for m in media:
        print(f"\nmídia {m['id']}: {m['name']} ({m['kind']}, {m.get('dur', 0):.1f}s) folha: {P / m['sheet']}")
    print(f"\nok. Próximo: klap.py cut {P} (use --drop para tirar erros/retakes, em tempos originais)")


def add_media(P, src, mid, credit=""):
    if not src.exists():
        sys.exit(f"não achei a mídia: {src}")
    ext = src.suffix.lower()
    sheet = P / "build" / f"{mid}_folha.jpg"
    if ext in IMG_EXT:
        out = P / "assets" / "media" / f"{mid}.jpg"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "scale='min(1440,iw)':-2", "-q:v", "2", str(out)])
        shutil.copy2(out, sheet)
        info = probe(out)
        return {"id": mid, "name": src.name, "kind": "image", "src": f"assets/media/{mid}.jpg", "w": info["w"],
                "h": info["h"], "dur": 0, "sheet": f"build/{mid}_folha.jpg", "credit": credit}
    out = P / "assets" / "media" / f"{mid}.mp4"
    print(f"preparando mídia {src.name}")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf",
         f"scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))',fps={FPS},format=yuv420p",
         "-c:v", "libx264", "-crf", "19", "-preset", "fast", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
         "-movflags", "+faststart", str(out)])
    info = probe(out)
    n = 6
    step = max(info["dur"] / n, 0.1)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf",
         f"fps=1/{step:.3f},scale=240:-2,tile={n}x1", "-frames:v", "1", str(sheet)])
    return {"id": mid, "name": src.name, "kind": "video", "src": f"assets/media/{mid}.mp4", "w": info["w"],
            "h": info["h"], "dur": round(info["dur"], 3), "sheet": f"build/{mid}_folha.jpg",
            "sheetStep": round(step, 3), "credit": credit}


def cmd_media(a):
    P = proj(a.projeto)
    st = state(P)
    for e in a.arquivos:
        m = add_media(P, Path(e).expanduser().resolve(), next_media_id(P, st))
        st.setdefault("media", []).append(m)
        print(f"mídia {m['id']}: {m['name']} folha: {P / m['sheet']}")
    save_state(P, st)


# ---------------------------------------------------------------- cut
def parse_ranges(s):
    out = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        x, y = part.split("-")
        out.append([float(x), float(y)])
    return out


def subtract(segs, cuts):
    for c0, c1 in cuts:
        nxt = []
        for a, b in segs:
            if c1 <= a or c0 >= b:
                nxt.append([a, b])
                continue
            if c0 > a:
                nxt.append([a, c0])
            if c1 < b:
                nxt.append([c1, b])
        segs = nxt
    return segs


def cmd_cut(a):
    P = proj(a.projeto)
    st = state(P)
    if not st:
        sys.exit("rode o prep primeiro")
    dur = st["rawDur"]
    pad = a.pad
    words = st["wordsRaw"]
    # pausas longas = silêncio do ffmpeg maior que gap; mantém um respiro (pad) de cada lado
    cuts = []
    for s0, s1 in st["silences"]:
        if s1 - s0 >= a.gap:
            c0, c1 = s0 + pad, s1 - pad
            if s0 <= 0.01:
                c0 = 0.0
            if s1 >= dur - 0.01:
                c1 = dur
            if c1 > c0:
                cuts.append([c0, c1])
    # pausas que o Whisper vê entre palavras (pega pausa mesmo com música de fundo)
    for w0, w1 in zip(words, words[1:]):
        if w1["s"] - w0["e"] >= max(a.gap, 0.45):
            cuts.append([w0["e"] + pad + 0.05, w1["s"] - pad])
    # o início e o fim, até a primeira/última palavra
    if words:
        cuts.append([0.0, max(0.0, words[0]["s"] - 0.12)])
        cuts.append([min(dur, words[-1]["e"] + 0.35), dur])
    cuts += parse_ranges(a.drop)
    segs = subtract([[0.0, dur]], sorted(cuts))
    segs = [[round(x, 3), round(y, 3)] for x, y in segs if y - x >= 0.12]
    if not segs:
        sys.exit("nada sobrou depois dos cortes")
    speed = a.speed
    # monta o filtro
    parts, labels = [], []
    for i, (x, y) in enumerate(segs):
        L = y - x
        fo = max(0.0, L - 0.012)
        parts.append(f"[0:v]trim=start={x}:end={y},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={x}:end={y},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,"
                     f"afade=t=out:st={fo:.3f}:d=0.012[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    parts.append("".join(labels) + f"concat=n={len(segs)}:v=1:a=1[vc][ac]")
    clean = "highpass=f=80,afftdn=nf=-25," if not a.no_clean else ""
    parts.append(f"[vc]setpts=PTS/{speed},fps={FPS}[vo]")
    parts.append(f"[ac]atempo={speed},{clean}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[ao]")
    fpath = P / "build" / "cut_filter.txt"
    fpath.write_text(";\n".join(parts))
    out = P / "assets" / "cut.mp4"
    print(f"cortando {len(segs)} trechos, velocidade {speed}x ...")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(P / st["raw"]), "-/filter_complex", str(fpath),
         "-map", "[vo]", "-map", "[ao]", "-c:v", "libx264", "-crf", "17", "-preset", "fast",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    # remapeia as palavras
    offs, o = [], 0.0
    for x, y in segs:
        offs.append(o)
        o += y - x
    ew = []
    dropped = parse_ranges(a.drop)
    for w in words:
        mid = (w["s"] + w["e"]) / 2
        if any(d0 <= mid <= d1 for d0, d1 in dropped):
            continue
        # o trecho que contém a palavra; se o Whisper errou o tempo um pouco, o trecho mais próximo
        best, dist = None, 9e9
        for k, (x, y) in enumerate(segs):
            d = 0 if x - 0.05 <= mid <= y + 0.05 else min(abs(mid - x), abs(mid - y))
            if d < dist:
                best, dist = k, d
        if best is None or dist > 0.6:
            continue
        (x, y), off = segs[best], offs[best]
        ws_, we_ = min(max(w["s"], x), y - 0.04), min(max(w["e"], x + 0.04), y)
        s = (off + ws_ - x) / speed
        e = (off + we_ - x) / speed
        ew.append({"w": w["w"], "s": round(s, 3), "e": round(max(e, s + 0.04), 3)})
    cdur = probe(out)["dur"]
    # transcreve de novo o vídeo já cortado: tempos de palavra mais certos que o remapeamento
    # (o Whisper estica palavras quando há vento/ruído ou retakes no bruto)
    cwav = P / "build" / "cut16k.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vn", "-ac", "1", "-ar", "16000", str(cwav)])
    tw = transcribe(cwav, P / "build" / "whisper_cut")
    for w in tw:
        w["e"] = round(min(w["e"], cdur), 3)
        w["s"] = round(min(w["s"], w["e"] - 0.04), 3)
    if tw and len(tw) >= 0.6 * len(ew):
        ew = tw
    st.update({"cut": "assets/cut.mp4", "cutDur": round(cdur, 3), "speed": speed, "segments": segs,
               "drop": parse_ranges(a.drop), "words": ew})
    print("procurando o rosto...")
    run([str(VISION), "face", str(out), str(P / "build" / "face.json"), "0.5"])
    st["face"] = load(P / "build" / "face.json")["median"]
    st.pop("cutout", None)
    save_state(P, st)
    (P / "build" / "transcricao_editada.txt").write_text(transcript_lines(ew, gap=0.3))
    print(f"\nok: {st['rawDur']:.1f}s -> {cdur:.1f}s ({len(segs)} trechos)")
    print("TRANSCRIÇÃO EDITADA (tempos de edição):")
    print(transcript_lines(ew, gap=0.3))


# ---------------------------------------------------------------- matte
def cmd_matte(a):
    P = proj(a.projeto)
    st = state(P)
    if "cut" not in st:
        sys.exit("rode o cut primeiro")
    mask = P / "build" / "mask.mp4"
    print("recortando a pessoa (Vision)...")
    run([str(VISION), "matte", str(P / st["cut"]), str(mask), a.quality])
    out = P / "assets" / "cutout.webm"
    print("gerando vídeo transparente (VP9 com alfa)...")
    outline = "" if a.no_outline else (
        f"[mo]scale={W // 2}:{H // 2},dilation,dilation,dilation,dilation,scale={W}:{H},gblur=sigma=1.5[md];"
        f"color=c=white:s={W}x{H}:r={FPS}[wc];[wc][md]alphamerge[ring];[ring][person]overlay=shortest=1,format=yuva420p[o]")
    split_m = "split=2[m][mo];" if outline else ""
    person = "[0:v][m]alphamerge,format=yuva420p" + ("[person];" if outline else "[o]")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(P / st["cut"]), "-i", str(mask), "-filter_complex",
         f"[1:v]scale={W}:{H},format=gray,tmix=frames=3,gblur=sigma=1.2,curves=all='0/0 0.35/0.1 0.6/0.9 1/1',"
         f"{split_m if outline else ''}" + ("" if outline else "null[m];") + person + outline,
         "-map", "[o]", "-an", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "6M", "-deadline", "realtime",
         "-cpu-used", "8", "-row-mt", "1", "-auto-alt-ref", "0", str(out)])
    st["cutout"] = "assets/cutout.webm"
    st["cutoutOutline"] = not a.no_outline
    save_state(P, st)
    print(f"ok -> {out}")


# ---------------------------------------------------------------- autoplan
def clean_word(w):
    return re.sub(r"[^\wÀ-ÿ-]", "", w).lower()


def pick_keyword(ws):
    best, score = None, 0
    for w in ws:
        c = clean_word(w["w"])
        if c in STOP or len(c) < 4:
            continue
        sc = len(c) + (3 if re.search(r"\d", c) else 0)
        if sc > score:
            best, score = re.sub(r"[\.,!?;:…]+$", "", w["w"]), sc
    return best or ""


def make_scenes(words, dur, maxlen, minlen):
    if not words:
        return [{"start": 0.0, "end": dur, "w0": 0, "w1": -1}]
    groups, cur = [], [0]
    for i in range(1, len(words)):
        prev = words[i - 1]
        L = words[i - 1]["e"] - words[cur[0]]["s"]
        brk = (re.search(r"[\.!?…]$", prev["w"]) and L >= minlen) or (words[i]["s"] - prev["e"] > 0.3 and L >= minlen) \
            or (re.search(r"[,;:]$", prev["w"]) and L >= maxlen * 0.6) or L >= maxlen
        if brk:
            groups.append(cur)
            cur = []
        cur.append(i)
    groups.append(cur)
    # junta um final curto demais
    if len(groups) > 1 and words[groups[-1][-1]]["e"] - words[groups[-1][0]]["s"] < minlen * 0.6:
        groups[-2] += groups[-1]
        groups.pop()
    scenes = []
    for gi, g in enumerate(groups):
        start = 0.0 if gi == 0 else round(words[g[0]]["s"] - 0.04, 3)
        scenes.append({"start": start, "w0": g[0], "w1": g[-1]})
    for i, s in enumerate(scenes):
        s["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else round(dur, 3)
    return scenes


def make_captions(words, dur, mode, maxw, maxc, cuts):
    caps, cur = [], []
    cutset = set(cuts)

    def flush():
        if cur:
            caps.append({"start": cur[0]["s"], "words": cur[:]})
            cur.clear()

    for i, w in enumerate(words):
        if cur and (mode == "word" or len(cur) >= maxw or
                    len(" ".join(x["w"] for x in cur + [w])) > maxc or i in cutset or
                    re.search(r"[\.!?,;:…]$", cur[-1]["w"]) or w["s"] - cur[-1]["e"] > 0.35):
            flush()
        cur.append({"w": w["w"], "s": w["s"], "e": w["e"]})
    flush()
    for i, c in enumerate(caps):
        nxt = caps[i + 1]["start"] if i + 1 < len(caps) else dur
        c["end"] = round(min(nxt, c["words"][-1]["e"] + 0.6), 3)
        c["start"] = round(c["start"], 3)
    return caps


EMOJI = [
    (r"dinheiro|grana|r\$|reais|lucro|faturamento|faturar|fatura", "💰"),
    (r"vend[aeio]|cliente|compra", "💸"),
    (r"erro|errado|nunca|pare\b|parar|não faça|cuidado", "❌"),
    (r"certo|correto|funciona|resultado", "✅"),
    (r"ideia|dica|segredo|truque|estratégia", "💡"),
    (r"tempo|hora|minuto|rápido|rapidinho", "⏰"),
    (r"amor|amo|ama|paixão|coração", "❤️"),
    (r"viral|bomb|explod|fogo|quente", "🔥"),
    (r"cresc|subir|aument|escal|seguidor", "📈"),
    (r"instagram|celular|post|reels|story|stories", "📱"),
    (r"atenção|importante|alerta|aviso", "⚠️"),
    (r"pens|cabeça|mente|cérebro|psicol", "🧠"),
    (r"chocad|absurd|inacredit|surpres|choque", "😱"),
    (r"rir|risada|engraçad|piada", "😂"),
    (r"saúde|corpo|treino|academia|músculo", "💪"),
    (r"família|filho|mãe|pai|casamento|bebê|grávida|gravidez", "👶"),
    (r"casa|apartamento|imóvel", "🏠"),
    (r"comida|comer|doce|bolo|receita", "🍰"),
    (r"pergunt|dúvida|por que|porquê", "🤔"),
    (r"meta|objetivo|foco|alvo", "🎯"),
    (r"presente|bônus|grátis|de graça", "🎁"),
    (r"estud|curso|aula|aprend", "📚"),
]


def emoji_for(text):
    t = text.lower()
    for pat, e in EMOJI:
        if re.search(pat, t):
            return e
    return None


def auto_sfx(plan):
    """Sons automáticos a partir das transições, títulos, elementos e CTA (os manuais ficam)."""
    keep = [x for x in plan.get("sfx", []) if x.get("manual")]
    out = []
    vol = plan.get("style", {}).get("sfxVolume", 1.0)
    if plan.get("title", {}).get("text"):
        out.append({"t": max(0.0, plan["title"]["start"]), "name": "whoosh", "volume": 0.35 * vol})
    for sc in plan["scenes"][1:]:
        tr = sc.get("transition", "cut")
        if tr in ("slide", "zoomblur", "flash"):
            out.append({"t": max(0.0, sc["start"] - 0.12), "name": "whoosh", "volume": 0.32 * vol})
        elif tr == "punch":
            out.append({"t": sc["start"], "name": "hit", "volume": 0.22 * vol})
        if sc.get("keyword"):
            out.append({"t": sc["start"] + 0.05, "name": "pop", "volume": 0.25 * vol})
    for o in plan.get("overlays", []):
        n = {"notif": "notif", "search": "type", "counter": "riser", "stamp": "hit", "list": "pop"}.get(o["type"], "pop")
        out.append({"t": o["start"], "name": n, "volume": (0.3 if n != "type" else 0.2) * vol})
        if o["type"] == "counter":
            out.append({"t": o["start"] + 1.25, "name": "ding", "volume": 0.3 * vol})
        if o["type"] == "search":
            for k in range(1, min(14, len(o.get("text", "")))):
                out.append({"t": o["start"] + 0.2 + k * 0.053, "name": "type", "volume": 0.12 * vol})
    if plan.get("cta") and plan["cta"].get("text"):
        out.append({"t": plan["cta"]["start"], "name": "ding", "volume": 0.35 * vol})
    out = [x for x in out if x["t"] < plan["duration"] - 0.05]
    plan["sfx"] = sorted(keep + [{**x, "t": round(x["t"], 3), "volume": round(x["volume"], 3)} for x in out],
                         key=lambda x: x["t"])
    return plan


def copy_assets(P):
    (P / "sfx").mkdir(exist_ok=True)
    for f in (MOTOR / "sfx").glob("*.wav"):
        shutil.copy2(f, P / "sfx" / f.name)
    (P / "fonts").mkdir(exist_ok=True)
    for f in list(FONTS.glob("*.woff2")) + list(FONTS.glob("*.png")):
        shutil.copy2(f, P / "fonts" / f.name)


def cmd_autoplan(a):
    P = proj(a.projeto)
    st = state(P)
    if "cut" not in st:
        sys.exit("rode o cut primeiro")
    planf = P / "plan.json"
    if planf.exists() and not a.force:
        sys.exit(f"{planf} já existe (use --force para refazer do zero)")
    copy_assets(P)
    tpl = load(TEMPLATES / f"{a.template}.json")
    words, dur = st["words"], st["cutDur"]
    scenes = make_scenes(words, dur, tpl["sceneMax"], tpl["sceneMin"])
    media = [m for m in st.get("media", [])]
    pattern = tpl["pattern"]
    trans = tpl.get("transitions", ["cut"])
    used = {}
    mi = 0
    out_scenes = []
    for i, s in enumerate(scenes):
        ws = words[s["w0"]: s["w1"] + 1] if s["w1"] >= s["w0"] else []
        nin = len(tpl.get("intro", []))
        layout = pattern[(i - nin) % len(pattern)] if i >= nin else tpl["intro"][i]
        sc = {"id": i + 1, "start": s["start"], "end": s["end"], "layout": layout,
              "text": " ".join(w["w"] for w in ws)}
        if layout in ("split", "green", "media"):
            if media:
                m = media[mi % len(media)]
                mi += 1
                sc["media"] = m["id"]
                sc["mediaStart"] = round(used.get(m["id"], 0.0), 2)
                if m["kind"] == "video" and m["dur"]:
                    used[m["id"]] = (used.get(m["id"], 0.0) + (s["end"] - s["start"])) % max(m["dur"], 0.1)
            else:
                sc["layout"] = "full"
        if tpl.get("zoomPattern"):
            sc["zoom"] = tpl["zoomPattern"][i % len(tpl["zoomPattern"])]
        if tpl.get("keywords") and sc["layout"] in tpl["keywords"] and not (i == 0 and a.title):
            sc["keyword"] = pick_keyword(ws)
        sc["transition"] = "cut" if i == 0 else trans[(i - 1) % len(trans)]
        # mudança de layout pede transição com movimento
        if i > 0 and out_scenes[-1]["layout"] != sc["layout"] and sc["transition"] == "cut":
            sc["transition"] = "slide"
        out_scenes.append(sc)
    if tpl.get("needsCutout") and "cutout" not in st:
        print("aviso: este template usa a pessoa recortada; rode klap.py matte antes da prévia")
    cuts = [s["w0"] for s in scenes]
    caps = make_captions(words, dur, tpl["captionMode"], tpl.get("captionMaxWords", 4),
                         tpl.get("captionMaxChars", 22), cuts)
    # emojis automáticos (no máx. um a cada ~3.5 s, nunca na cena do título)
    overlays, last = [], -9.0
    if tpl.get("autoEmoji", True):
        for sc in out_scenes[1:]:
            e = emoji_for(sc["text"])
            if not e or sc["start"] - last < 3.5 or sc["end"] - sc["start"] < 1.0:
                continue
            pos = tpl.get("emojiPos", {}).get(sc["layout"], [0.82, 0.24])
            overlays.append({"type": "emoji", "emoji": e, "start": round(sc["start"] + 0.15, 3),
                             "end": round(min(sc["end"], sc["start"] + 1.6), 3), "x": pos[0], "y": pos[1],
                             "size": 230})
            last = sc["start"]
    style = dict(tpl["style"])
    style["captionMode"] = tpl["captionMode"]
    cta = None
    if a.cta:
        cta = {"text": a.cta, "sub": a.cta_sub or "", "start": round(max(0.0, dur - min(2.6, dur * 0.25)), 3)}
    plan = {
        "template": a.template,
        "fps": FPS, "width": W, "height": H,
        "duration": dur,
        "speaker": st["cut"],
        "cutout": st.get("cutout"),
        "face": st.get("face"),
        "title": {"text": a.title or "", "start": 0.0, "end": min(tpl.get("titleSeconds", 3.0), dur),
                  "highlight": a.highlight or ""},
        "style": style,
        "media": {m["id"]: {"src": m["src"], "kind": m["kind"], "dur": m.get("dur", 0), "name": m["name"],
                            "w": m.get("w"), "h": m.get("h"), "credit": m.get("credit", "")} for m in media},
        "scenes": out_scenes,
        "captions": caps,
        "overlays": overlays,
        "cta": cta,
        "music": None,
        "sfx": [],
    }
    if st.get("music"):
        plan["music"] = {"src": st["music"], "volume": tpl.get("musicVolume", 0.12), "duck": 0.35}
    auto_sfx(plan)
    save(planf, plan)
    print(f"plano criado: {len(out_scenes)} cenas, {len(caps)} legendas, {len(overlays)} emojis, "
          f"{len(plan['sfx'])} sons -> {planf}")
    for s in out_scenes:
        extra = f" mídia={s.get('media')}@{s.get('mediaStart', 0)}" if s.get("media") else ""
        kw = f" palavra={s['keyword']!r}" if s.get("keyword") else ""
        print(f"  cena {s['id']:>2} {s['start']:5.2f}-{s['end']:5.2f} {s['layout']:<6} {s['transition']:<8}{extra}{kw}"
              f" | {s['text']}")
    for o in overlays:
        print(f"  emoji {o['emoji']} {o['start']:.2f}-{o['end']:.2f}")


def cmd_sync(a):
    """Depois de editar o plan.json à mão: refaz os sons automáticos e confere o plano."""
    P = proj(a.projeto)
    plan = load(P / "plan.json")
    copy_assets(P)
    st = state(P)
    if st.get("cutout") and not plan.get("cutout"):
        plan["cutout"] = st["cutout"]
    for mid, m in ((m["id"], m) for m in st.get("media", [])):
        plan["media"].setdefault(mid, {"src": m["src"], "kind": m["kind"], "dur": m.get("dur", 0), "name": m["name"],
                                       "w": m.get("w"), "h": m.get("h"), "credit": m.get("credit", "")})
    if st.get("music") and not plan.get("music"):
        plan["music"] = {"src": st["music"], "volume": 0.12, "duck": 0.35}
    auto_sfx(plan)
    save(P / "plan.json", plan)
    check_plan(P, plan)
    print(f"ok: {len(plan['scenes'])} cenas, {len(plan.get('overlays', []))} elementos, {len(plan['sfx'])} sons")


# ---------------------------------------------------------------- buscar na internet (mídia livre)
UA = {"User-Agent": "klap-editor/1.0 (uso pessoal)"}


def http_json(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA["User-Agent"], url], capture_output=True)
    if r.returncode != 0:
        sys.exit(f"falha na busca ({url[:60]}...)")
    return json.loads(r.stdout.decode() or "{}")


def http_get(url, dest):
    r = subprocess.run(["curl", "-sL", "--fail", "--max-time", "300", "-A", UA["User-Agent"], "-o", str(dest), url])
    if r.returncode != 0:
        sys.exit(f"esse arquivo não está mais disponível na fonte ({url[:70]}...). Escolha outro número em --pegar.")


def cmd_buscar(a):
    """Procura mídia livre e (com --pegar) baixa para o projeto como nova mídia."""
    import urllib.parse
    P = proj(a.projeto)
    q = urllib.parse.quote(a.termo)
    res = []
    if a.tipo == "imagem":
        j = http_json(f"https://api.openverse.org/v1/images/?q={q}&license=cc0,pdm,by,by-sa&page_size={a.n}"
                      f"&mature=false&size=large")
        for r in j.get("results", []):
            res.append({"url": r["url"], "w": r.get("width"), "h": r.get("height"), "ext": ".jpg",
                        "titulo": r.get("title", ""), "credito": f"{r.get('creator') or '?'} ({r.get('license', '').upper()} "
                        f"{r.get('license_version', '')}) via {r.get('source', 'Openverse')}",
                        "pagina": r.get("foreign_landing_url", "")})
    elif a.tipo == "musica" or a.tipo == "som":
        extra = "&category=music" if a.tipo == "musica" else "&category=sound_effect"
        j = http_json(f"https://api.openverse.org/v1/audio/?q={q}&license=cc0,pdm,by,by-sa&page_size={a.n}{extra}")
        for r in j.get("results", []):
            res.append({"url": r["url"], "dur": (r.get("duration") or 0) / 1000, "ext": ".mp3",
                        "titulo": r.get("title", ""), "credito": f"{r.get('creator') or '?'} ({r.get('license', '').upper()})"
                        f" via {r.get('source', 'Openverse')}", "pagina": r.get("foreign_landing_url", "")})
    elif a.tipo == "video":
        api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6"
               f"&gsrsearch={q}%20filetype:video&gsrlimit={a.n}&prop=imageinfo&iiprop=url|size|extmetadata")
        j = http_json(api)
        for pg in (j.get("query", {}).get("pages", {}) or {}).values():
            ii = (pg.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata", {})
            res.append({"url": ii.get("url"), "w": ii.get("width"), "h": ii.get("height"), "ext": ".webm",
                        "titulo": pg.get("title", ""), "credito": f"{re.sub('<[^>]+>', '', md.get('Artist', {}).get('value', '?'))}"
                        f" ({md.get('LicenseShortName', {}).get('value', '?')}) via Wikimedia Commons",
                        "pagina": ii.get("descriptionurl", "")})
    elif a.tipo == "stock":
        # Mixkit: vídeos de banco com licença livre (só os que têm arquivo 2160p têm a licença comercial)
        tag = re.sub(r"[^a-z0-9]+", "-", a.termo.lower()).strip("-")
        r = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/124",
                            f"https://mixkit.co/free-stock-video/{tag}/"], capture_output=True)
        html = r.stdout.decode("utf-8", "replace")
        seen = []
        for slug, vid in re.findall(r"/free-stock-video/([a-z0-9-]+?)-(\d{3,6})/", html):
            if vid not in [x[1] for x in seen]:
                seen.append((slug, vid))
        ok = []
        for slug, vid in seen:
            if len(ok) >= a.n:
                break
            h = subprocess.run(["curl", "-sIL", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "15",
                                f"https://assets.mixkit.co/videos/{vid}/{vid}-2160.mp4"], capture_output=True, text=True)
            if h.stdout.strip() == "200":
                ok.append((slug, vid))
        for slug, vid in ok:
            res.append({"url": f"https://assets.mixkit.co/videos/{vid}/{vid}-2160.mp4", "ext": ".mp4",
                        "titulo": slug.replace("-", " "), "credito": "Mixkit Stock Video Free License (sem crédito obrigatório)",
                        "pagina": f"https://mixkit.co/free-stock-video/{slug}-{vid}/", "thumb":
                        f"https://assets.mixkit.co/videos/{vid}/{vid}-thumb-360-0.jpg"})
        if not seen and r.returncode == 0:
            print(f"(o Mixkit usa categorias em inglês de 1 ou 2 palavras: tente 'office', 'phone', 'city', 'sunset'...)")
    elif a.tipo == "youtube":
        r = subprocess.run(["yt-dlp", "--flat-playlist", "--playlist-end", str(a.n), "--print",
                            "%(id)s|%(duration)s|%(title)s|%(channel)s",
                            f"https://www.youtube.com/results?search_query={q}&sp=EgIwAQ%253D%253D"],
                           text=True, capture_output=True)
        for line in r.stdout.splitlines():
            vid, d, t, ch = (line.split("|") + ["", "", "", ""])[:4]
            res.append({"url": f"https://www.youtube.com/watch?v={vid}", "dur": float(d or 0), "ext": ".mp4",
                        "titulo": t, "credito": f"{ch} (CC BY) via YouTube", "pagina": f"https://youtu.be/{vid}"})
    for r in res:
        r["titulo"] = re.sub(r"<[^>]+>", "", r.get("titulo") or "").strip()
    if a.tipo == "stock" and res:
        th = P / "build" / "busca_stock"
        th.mkdir(parents=True, exist_ok=True)
        for f in th.glob("*.jpg"):
            f.unlink()
        for i, r in enumerate(res):
            subprocess.run(["curl", "-sL", "--max-time", "20", "-o", str(th / f"{i:02d}.jpg"), r["thumb"]])
        ok = sorted(str(f) for f in th.glob("*.jpg") if f.stat().st_size > 1000)
        if ok:
            cmd = ["ffmpeg", "-v", "error", "-y"]
            for f in ok:
                cmd += ["-i", f]
            n = len(ok)
            flt = "".join(f"[{i}]scale=320:180:force_original_aspect_ratio=increase,crop=320:180,"
                          f"drawbox=0:0:44:30:black@0.7:fill,setsar=1[v{i}];" for i in range(n))
            flt += "".join(f"[v{i}]" for i in range(n)) + f"xstack=inputs={n}:layout=" + "|".join(
                f"{(i % 4) * 320}_{(i // 4) * 180}" for i in range(n)) + ":fill=black" if n > 1 else "[v0]null"
            subprocess.run(cmd + ["-filter_complex", flt, str(P / "build" / "busca_stock.jpg")])
            print(f"miniaturas (ordem 0,1,2... da esquerda pra direita): {P / 'build' / 'busca_stock.jpg'}")
    for i, r in enumerate(res):
        dim = f"{r.get('w')}x{r.get('h')}" if r.get("w") else f"{r.get('dur', 0):.0f}s"
        print(f"[{i}] {dim} {r['titulo'][:70]} | {r['credito'][:80]}")
    if not res:
        print("nada encontrado; tente outro termo (em inglês costuma ter mais)")
        return
    if a.pegar is None:
        print("\nPara baixar: repita com --pegar <número> (vídeo do YouTube: --trecho 10-25)")
        return
    r = res[a.pegar]
    st = state(P)
    tmpd = P / "build" / "baixados"
    tmpd.mkdir(parents=True, exist_ok=True)
    dest = tmpd / f"busca_{len(list(tmpd.iterdir())) + 1}{r['ext']}"
    if a.tipo == "youtube":
        sec = a.trecho or "0-15"
        subprocess.run(["yt-dlp", "-q", "--no-warnings", "-f", "bv*[height<=1080][ext=mp4]+ba/b[height<=1080]",
                        "--download-sections", f"*{sec}", "--force-keyframes-at-cuts", "--merge-output-format", "mp4",
                        "-o", str(dest), r["url"]], check=True)
    else:
        http_get(r["url"], dest)
    credit = f"{r['titulo']} | {r['credito']} | {r['pagina']}"
    with open(P / "creditos.txt", "a") as f:
        f.write(credit + "\n")
    if a.tipo == "musica":
        out = P / "assets" / "media" / "musica.mp3"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(dest), "-vn", "-ac", "2", "-ar", "48000", "-b:a", "192k", str(out)])
        st["music"] = "assets/media/musica.mp3"
        save_state(P, st)
        print(f"música salva: {out} (crédito em creditos.txt). Rode klap.py sync para ligar no plano.")
        return
    m = add_media(P, dest, next_media_id(P, st), credit)
    st.setdefault("media", []).append(m)
    save_state(P, st)
    print(f"mídia {m['id']} adicionada ({m['kind']}). Folha: {P / m['sheet']}. Crédito em creditos.txt")


# ---------------------------------------------------------------- render (Remotion)
def ensure_remotion():
    nm = REMOTION / "node_modules"
    if (nm / "remotion").exists():
        return
    print("instalando o Remotion (npm install)...")
    run(["npm", "install", "--no-audit", "--no-fund"], cwd=str(REMOTION))


def check_plan(P, plan):
    errs = []
    if not (P / plan["speaker"]).exists():
        errs.append(f"vídeo da pessoa não existe: {plan['speaker']}")
    prev = 0.0
    for s in plan["scenes"]:
        if s["end"] <= s["start"]:
            errs.append(f"cena {s['id']}: fim <= início")
        if abs(s["start"] - prev) > 0.02:
            errs.append(f"cena {s['id']}: começa em {s['start']} mas a anterior termina em {prev} (buraco/sobreposição)")
        prev = s["end"]
        if s["layout"] in ("split", "green", "media"):
            m = s.get("media")
            if not m or m not in plan["media"]:
                errs.append(f"cena {s['id']}: layout {s['layout']} precisa de 'media' válida")
        if s["layout"] == "green" and not plan.get("cutout"):
            errs.append(f"cena {s['id']}: tela verde sem recorte (rode klap.py matte e refaça o 'cutout' no plano)")
    if abs(prev - plan["duration"]) > 0.05:
        errs.append(f"as cenas terminam em {prev} mas o vídeo tem {plan['duration']}")
    big = sorted([o for o in plan.get("overlays", []) if o.get("type") not in ("emoji", "notif")], key=lambda o: o["start"])
    for o1, o2 in zip(big, big[1:]):
        if o2["start"] < o1["end"] - 0.05:
            errs.append(f"elementos {o1['type']} ({o1['start']}-{o1['end']}s) e {o2['type']} ({o2['start']}s) se sobrepõem")
    for o in plan.get("overlays", []):
        if o.get("type") == "card" and o.get("media") not in plan["media"]:
            errs.append(f"elemento card em {o.get('start')}s: mídia {o.get('media')} não existe no plano")
        if o.get("end", 0) <= o.get("start", 0):
            errs.append(f"elemento {o.get('type')} em {o.get('start')}s: fim <= início")
    if plan.get("music") and not (P / plan["music"]["src"]).exists():
        errs.append(f"música não existe: {plan['music']['src']}")
    for m in plan["media"].values():
        if not (P / m["src"]).exists():
            errs.append(f"mídia não existe: {m['src']}")
    if errs:
        sys.exit("plano com problema:\n  " + "\n  ".join(errs))


def remotion_render(P, out, scale, frames=None, crf=18):
    ensure_remotion()
    plan = load(P / "plan.json")
    copy_assets(P)
    st = state(P)
    if st.get("cutout") and not plan.get("cutout"):
        plan["cutout"] = st["cutout"]
        save(P / "plan.json", plan)
    check_plan(P, plan)
    cmd = ["npx", "remotion", "render", "src/index.ts", "Reel", str(out), f"--props={P / 'plan.json'}",
           f"--public-dir={P}", f"--scale={scale}", "--codec=h264", f"--crf={crf}", "--log=error",
           f"--concurrency={max(2, (os.cpu_count() or 8) - 2)}", "--image-format=jpeg", "--jpeg-quality=92",
           "--offthreadvideo-cache-size-in-bytes=1500000000"]
    if frames:
        cmd.append(f"--frames={frames}")
    print(f"renderizando ({'prévia' if scale < 1 else 'final'})...")
    r = subprocess.run(cmd, cwd=str(REMOTION), text=True)
    if r.returncode != 0:
        sys.exit("o Remotion falhou (veja o erro acima)")


def cmd_preview(a):
    P = proj(a.projeto)
    plan = load(P / "plan.json")
    out = P / "build" / "previa.mp4"
    frames = None
    if a.seconds:
        frames = f"0-{min(int(a.seconds * FPS), int(plan['duration'] * FPS)) - 1}"
    remotion_render(P, out, 0.5, frames, crf=23)
    storyboard(P, out, partial=bool(a.seconds))
    if not a.no_open:
        subprocess.run(["open", str(P / "storyboard.html")])
    print(f"ok: prévia {out}\nstoryboard {P / 'storyboard.html'}")


def storyboard(P, preview, partial=False):
    plan = load(P / "plan.json")
    th = P / "build" / "thumbs"
    if th.exists():
        shutil.rmtree(th)
    th.mkdir(parents=True)
    pdur = probe(preview)["dur"]
    cards = []
    for s in plan["scenes"]:
        t = (s["start"] + s["end"]) / 2
        img = ""
        if t < pdur - 0.05:
            f = th / f"cena{s['id']:02d}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(preview), "-frames:v", "1",
                           "-vf", "scale=270:-2", "-q:v", "3", str(f)])
            if f.exists():
                img = f"build/thumbs/{f.name}"
        caps = [c for c in plan["captions"] if c["start"] < s["end"] and c["end"] > s["start"]]
        legend = " / ".join(" ".join(w["w"] for w in c["words"]) for c in caps)
        m = plan["media"].get(s.get("media", ""), {})
        cards.append({"id": s["id"], "t": f"{s['start']:.2f}–{s['end']:.2f}s", "layout": s["layout"],
                      "img": img, "legend": legend, "media": m.get("name", ""),
                      "keyword": s.get("keyword", ""), "zoom": s.get("zoom", "")})
    html = STORY_HTML.replace("__DATA__", json.dumps({
        "title": plan["title"].get("text", ""), "template": plan["template"], "dur": plan["duration"],
        "partial": partial, "cards": cards}, ensure_ascii=False))
    (P / "storyboard.html").write_text(html)


LAYOUT_PT = {"full": "você em tela cheia", "split": "tela dividida", "green": "tela verde",
             "media": "só a mídia", "word": "palavra grande"}

STORY_HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Storyboard KLAP</title>
<style>
:root{--bg:#f6f4f1;--fg:#16130f;--mut:#6b645b;--card:#fff;--line:#e4dfd8;--acc:#b3123a}
@media (prefers-color-scheme:dark){:root{--bg:#141210;--fg:#f2eee8;--mut:#a39b90;--card:#1f1c19;--line:#332e29;--acc:#ff4d73}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 -apple-system,system-ui,sans-serif}
header{display:flex;gap:24px;align-items:flex-start;padding:24px;border-bottom:1px solid var(--line);flex-wrap:wrap}
video{width:270px;border-radius:14px;background:#000}
h1{font-size:22px;margin:0 0 6px}.mut{color:var(--mut)}
.tip{margin-top:14px;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);max-width:560px}
code{background:var(--line);padding:1px 6px;border-radius:5px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;padding:24px}
.c{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.c img{width:100%;aspect-ratio:9/16;object-fit:cover;display:block;background:#000}
.ph{width:100%;aspect-ratio:9/16;display:grid;place-items:center;background:var(--line);color:var(--mut);font-size:13px}
.b{padding:10px 12px}.n{display:inline-block;background:var(--acc);color:#fff;border-radius:99px;padding:0 9px;font-weight:700;font-size:13px}
.t{font-size:12px;color:var(--mut);margin-left:6px}.l{font-weight:600;margin:6px 0 4px}.s{font-size:13px;color:var(--mut)}
</style></head><body><header>
<video src="build/previa.mp4" controls playsinline></video>
<div><h1 id="h"></h1><div class="mut" id="sub"></div>
<div class="tip">Quer mudar algo? Diga no chat do Claude a cena e o que mudar, por exemplo:<br>
<code>cena 3: troca o fundo pela mídia m2</code> · <code>legenda maior</code> · <code>cena 5 em tela cheia</code><br>
Quando estiver bom, diga <b>pode fazer</b> e ele renderiza o vídeo final.</div></div></header>
<div class="grid" id="g"></div>
<script>
const D=__DATA__;const LP={"full":"você em tela cheia","split":"tela dividida","green":"tela verde","media":"só a mídia","word":"palavra grande"};
document.getElementById('h').textContent=D.title||'Storyboard';
document.getElementById('sub').textContent='template '+D.template+' · '+D.dur.toFixed(1)+'s · '+D.cards.length+' cenas'+(D.partial?' · prévia parcial':'');
const g=document.getElementById('g');
for(const c of D.cards){const el=document.createElement('div');el.className='c';
const pic=c.img?`<img src="${c.img}" alt="">`:`<div class="ph">fora da prévia</div>`;
const esc=s=>String(s).replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));
el.innerHTML=pic+`<div class="b"><span class="n">${c.id}</span><span class="t">${c.t}</span>
<div class="l">${esc(LP[c.layout]||c.layout)}${c.media?' · '+esc(c.media):''}</div>
${c.keyword?`<div class="s">palavra: <b>${esc(c.keyword)}</b></div>`:''}
<div class="s">“${esc(c.legend)}”</div></div>`;g.appendChild(el);}
</script></body></html>"""


def limit_audio(path):
    """Segura o pico do áudio final em -1 dB (voz + sons + música somados podem estourar)."""
    tmp = Path(str(path) + ".lim.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-c:v", "copy", "-af",
         "alimiter=limit=0.89:attack=3:release=50:level=false", "-c:a", "aac", "-b:a", "256k",
         "-movflags", "+faststart", str(tmp)])
    tmp.replace(path)


def cmd_render(a):
    P = proj(a.projeto)
    plan = load(P / "plan.json")
    name = a.name or (plan["title"].get("text") or P.name)
    name = re.sub(r"[^\w\s\-À-ÿ]", "", name).strip()[:60] or "reel"
    out = P / "final" / f"{name}.mp4"
    remotion_render(P, out, 1, crf=16)
    limit_audio(out)
    info = probe(out)
    print(f"ok: {out} ({info['w']}x{info['h']}, {info['dur']:.1f}s)")
    if not a.no_open:
        subprocess.run(["open", "-R", str(out)])


def cmd_status(a):
    P = proj(a.projeto)
    st = state(P)
    print(json.dumps({k: st.get(k) for k in ["source", "rawDur", "cutDur", "speed", "cutout", "face"]},
                     ensure_ascii=False, indent=1))
    print("mídias:", [(m["id"], m["name"]) for m in st.get("media", [])])
    print("plan.json:", (P / "plan.json").exists(), "| prévia:", (P / "build/previa.mp4").exists())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prep")
    p.add_argument("projeto")
    p.add_argument("principal")
    p.add_argument("extras", nargs="*")
    p = sp.add_parser("media")
    p.add_argument("projeto")
    p.add_argument("arquivos", nargs="+")
    p = sp.add_parser("cut")
    p.add_argument("projeto")
    p.add_argument("--speed", type=float, default=1.2)
    p.add_argument("--drop", default="")
    p.add_argument("--gap", type=float, default=0.25)
    p.add_argument("--pad", type=float, default=0.07)
    p.add_argument("--no-clean", action="store_true")
    p = sp.add_parser("matte")
    p.add_argument("projeto")
    p.add_argument("--quality", default="accurate", choices=["fast", "balanced", "accurate"])
    p.add_argument("--no-outline", action="store_true")
    p = sp.add_parser("autoplan")
    p.add_argument("projeto")
    p.add_argument("--template", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--highlight", default="")
    p.add_argument("--cta", default="")
    p.add_argument("--cta-sub", default="")
    p.add_argument("--force", action="store_true")
    p = sp.add_parser("sync")
    p.add_argument("projeto")
    p = sp.add_parser("buscar")
    p.add_argument("projeto")
    p.add_argument("termo")
    p.add_argument("--tipo", default="imagem", choices=["imagem", "video", "stock", "musica", "som", "youtube"])
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--pegar", type=int)
    p.add_argument("--trecho", default="")
    p = sp.add_parser("preview")
    p.add_argument("projeto")
    p.add_argument("--seconds", type=float, default=0)
    p.add_argument("--no-open", action="store_true")
    p = sp.add_parser("render")
    p.add_argument("projeto")
    p.add_argument("--name", default="")
    p.add_argument("--no-open", action="store_true")
    p = sp.add_parser("status")
    p.add_argument("projeto")
    a = ap.parse_args()
    {"prep": cmd_prep, "media": cmd_media, "cut": cmd_cut, "matte": cmd_matte, "autoplan": cmd_autoplan,
     "sync": cmd_sync, "buscar": cmd_buscar,
     "preview": cmd_preview, "render": cmd_render, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
