import os, re, json, time, subprocess, urllib.request, html, datetime, pathlib, sys

KEY = os.environ["NVIDIA_API_KEY"]
TG = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
TASK = (os.environ.get("TASK") or "").strip() or "파이썬으로 할 수 있는 재미있는 작은 실험 하나를 스스로 골라서 해 봐"
MODEL = os.environ.get("LAB_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
REPO = os.environ.get("GITHUB_REPOSITORY", "buriburiyj/jun-lab")
OWNER, NAME = REPO.split("/")
SITE = f"https://{OWNER.lower()}.github.io/{NAME}/"
TRIES = 4
F = chr(96) * 3

SYS = f"""너는 리눅스(Ubuntu, Python 3.12) 컴퓨터에서 혼자 연구하는 연구원이다.
주어진 주제를 실제로 실험하는 파이썬 프로그램 하나를 작성한다.
답은 반드시 이 형식으로만 쓴다:
TITLE: 연구 제목(한국어, 짧게)
PIP: 필요한 pip 패키지 이름들(공백으로 구분, 없으면 비워 둠)
{F}python
전체 코드
{F}
규칙: 15분 안에 끝나야 한다. 결과와 숫자는 print로 자세히 출력한다.
그림을 만들면 out 폴더에 png로 저장한다(matplotlib는 Agg 사용, 글자는 영어로).
input()을 쓰지 않는다. 다른 컴퓨터를 공격하거나 스캔하지 않는다."""

def tg(msg):
    if not (TG and CHAT):
        return
    try:
        data = json.dumps({"chat_id": CHAT, "text": msg[:4000]}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{TG}/sendMessage", data, {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30)
    except Exception as e:
        print("텔레그램 실패", e, flush=True)

def ask(msgs, tokens=16000):
    body = json.dumps({"model": MODEL, "messages": msgs, "max_tokens": tokens, "temperature": 0.6}).encode()
    for i in range(3):
        try:
            req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", body,
                                         {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=600))
            return r["choices"][0]["message"].get("content") or ""
        except Exception as e:
            print("모델 실패", i + 1, e, flush=True)
            time.sleep(20)
    return ""

def parse(t):
    title = re.search(r"TITLE:\s*(.+)", t)
    pip = re.search(r"PIP:[ \t]*(.*)", t)
    code = re.search(F + r"(?:python)?[ \t]*\n(.*?)" + F, t, re.S)
    return (title.group(1).strip() if title else "연구",
            pip.group(1).split() if pip else [],
            code.group(1) if code else "")

def run(code, pkgs, d):
    pathlib.Path(d, "out").mkdir(parents=True, exist_ok=True)
    pathlib.Path(d, "main.py").write_text(code, encoding="utf-8")
    log = ""
    if pkgs:
        p = subprocess.run([sys.executable, "-m", "pip", "install", "-q", *pkgs], capture_output=True, text=True, timeout=600)
        log += (p.stdout + p.stderr)[-2000:]
    env = {k: v for k, v in os.environ.items() if "TOKEN" not in k and "KEY" not in k}
    env["MPLBACKEND"] = "Agg"
    try:
        p = subprocess.run([sys.executable, "main.py"], cwd=d, capture_output=True, text=True, timeout=900, env=env)
        out = log + p.stdout[-8000:]
        if p.returncode:
            out += "\n[오류]\n" + p.stderr[-4000:]
        return p.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, log + "15분 시간 초과"

def esc(s):
    return html.escape(s or "")

def page(title, ok, summary, code, out, imgs, tries):
    pics = "".join(f'<img src="out/{esc(i)}">' for i in imgs)
    state = "성공" if ok else "실패"
    return f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<style>body{{font-family:sans-serif;max-width:860px;margin:auto;padding:16px;line-height:1.6}}
pre{{background:#f4f4f4;padding:12px;overflow:auto;white-space:pre-wrap}}img{{max-width:100%}}</style>
<p><a href="../">← 연구 목록</a></p><h1>{esc(title)}</h1>
<p>주제: {esc(TASK)}<br>결과: {state} · 시도 {tries}번 · 모델 {esc(MODEL)}</p>
<h2>정리</h2><p>{esc(summary).replace(chr(10), "<br>")}</p>{pics}
<h2>실행 결과</h2><pre>{esc(out)}</pre><h2>코드</h2><pre>{esc(code)}</pre></html>"""

def index():
    items = []
    for m in pathlib.Path("docs").glob("*/meta.json"):
        try:
            items.append(json.loads(m.read_text(encoding="utf-8")))
        except Exception:
            pass
    items.sort(key=lambda x: x["id"], reverse=True)
    rows = "".join(f'<li><a href="{x["id"]}/">{esc(x["title"])}</a> · {x["id"]} · {"성공" if x["ok"] else "실패"}</li>' for x in items)
    pathlib.Path("docs/index.html").write_text(f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>준봇 연구소</title>
<body style="font-family:sans-serif;max-width:860px;margin:auto;padding:16px"><h1>준봇 연구소</h1><ul>{rows}</ul></body></html>""", encoding="utf-8")

def main():
    rid = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y%m%d-%H%M%S")
    d = f"docs/{rid}"
    pathlib.Path(d).mkdir(parents=True, exist_ok=True)
    tg("🔬 연구 시작: " + TASK[:300])
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": "주제: " + TASK}]
    ok, out, title, code, n = False, "", "연구", "", 0
    for n in range(1, TRIES + 1):
        t = ask(msgs)
        title, pkgs, code = parse(t)
        if not code:
            out = "모델이 코드를 주지 않았어요."
            msgs += [{"role": "assistant", "content": t or "(빈 답)"}, {"role": "user", "content": "형식을 지켜서 전체 코드를 다시 써."}]
            continue
        ok, out = run(code, pkgs, d)
        print(f"시도 {n}: {'성공' if ok else '실패'}", flush=True)
        if ok:
            break
        msgs += [{"role": "assistant", "content": t}, {"role": "user", "content": "실행했더니 문제가 생겼어. 고친 전체 코드를 같은 형식으로 다시 써.\n" + out[-3000:]}]
    summary = ask([{"role": "user", "content": f"주제: {TASK}\n\n코드:\n{code[:6000]}\n\n실행 결과:\n{out[-6000:]}\n\n"
                    "이 연구를 한국어로 쉽게 정리해 줘: 무엇을 했는지, 결과, 알게 된 점, 다음에 해 볼 것. 마크다운 기호 없이 평문으로."}], 6000) or "정리 실패"
    imgs = sorted(p.name for p in pathlib.Path(d, "out").glob("*.png"))
    pathlib.Path(d, "index.html").write_text(page(title, ok, summary, code, out, imgs, n), encoding="utf-8")
    pathlib.Path(d, "meta.json").write_text(json.dumps({"id": rid, "title": title, "ok": ok, "task": TASK}, ensure_ascii=False), encoding="utf-8")
    index()
    link = SITE + rid + "/"
    if ok:
        tg(f"✅ 연구 완료: {title}\n\n{summary[:1500]}\n\n보고서(1~2분 뒤 열림): {link}")
    else:
        tg(f"❓ {TRIES}번 시도했지만 잘 안 됐어요: {title}\n주제를 조금 더 자세히 알려 주세요.\n기록: {link}")

if __name__ == "__main__":
    main()
