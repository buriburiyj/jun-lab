import os, re, json, time, subprocess, urllib.request, urllib.parse, html, datetime, pathlib, shutil

KEY = os.environ["NVIDIA_API_KEY"]
TAVILY = os.environ.get("TAVILY_API_KEY", "")
TG = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
TASK = (os.environ.get("TASK") or "").strip() or "인터넷에서 흥미로운 주제를 하나 찾아서 직접 실험해 봐"
MODEL = os.environ.get("LAB_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
REPO = os.environ.get("GITHUB_REPOSITORY", "buriburiyj/jun-lab")
OWNER, NAME = REPO.split("/")
SITE = f"https://{OWNER.lower()}.github.io/{NAME}/"
MAX_STEPS = int(os.environ.get("MAX_STEPS", "40"))
LIMIT = 70 * 60
WS = pathlib.Path.home() / "ws"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
ENV = {k: v for k, v in os.environ.items() if not re.search("TOKEN|KEY|SECRET", k)}
ENV["MPLBACKEND"] = "Agg"

SYS = """너는 리눅스(Ubuntu) 컴퓨터를 혼자 쓰는 연구원이다. 인터넷 검색, 웹페이지 읽기, 터미널 명령 실행, 파일 쓰기를 할 수 있다.
작업 폴더는 ~/ws 이고 명령은 거기서 실행된다. sudo, apt, pip, git, curl 모두 쓸 수 있다.
한 번에 행동 하나만 한다. 답은 반드시 이 형식으로만 쓴다:
ACTION: search 또는 fetch 또는 shell 또는 write 또는 done 또는 ask
ARG: 한 줄 값
BODY:
여러 줄 내용
END

행동 설명:
search: ARG에 검색어. BODY는 비운다.
fetch: ARG에 웹 주소. 페이지 글자를 읽어 온다.
shell: BODY에 bash 명령. 5분 안에 끝나야 한다.
write: ARG에 파일 경로(작업 폴더 기준), BODY에 파일 전체 내용.
done: ARG에 연구 제목(한국어, 짧게), BODY에 한국어 정리(무엇을 했는지, 결과 숫자, 알게 된 점, 다음에 해 볼 것). 마크다운 기호 없이 평문.
ask: 여러 번 고쳐도 막히거나 사용자 정보가 꼭 필요할 때만. ARG에 사용자에게 할 질문.
규칙: 결과를 직접 실행해서 확인한 뒤에만 done 한다. 그림과 결과 파일은 ~/ws/out 폴더에 저장한다(그래프는 png, matplotlib Agg, 그래프 글자는 영어).
input()이나 끝나지 않는 서버를 실행하지 않는다(필요하면 timeout 명령 사용). 다른 컴퓨터를 공격하거나 스캔하지 않는다. 키나 비밀번호를 찾으려 하지 않는다."""

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

def clip(s, n=4000):
    s = s or ""
    return s if len(s) <= n else s[:n // 2] + "\n...(중략)...\n" + s[-n // 2:]

def strip_tags(t):
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def parse(t):
    t = t or ""
    head = t.split("BODY:")[0]
    a = re.search(r"ACTION:\s*(\w+)", head)
    if not a:
        return None, "", ""
    arg = re.search(r"ARG:[ \t]*(.*)", head)
    body = ""
    if "BODY:" in t:
        body = t.split("BODY:", 1)[1].lstrip(" \t").removeprefix("\n")
        m = re.search(r"(^|\n)END[ \t]*(\n|$)", body)
        if m:
            body = body[:m.start()]
    return a.group(1).lower(), (arg.group(1).strip() if arg else ""), body

def search(q):
    try:
        data = urllib.parse.urlencode({"q": q}).encode()
        req = urllib.request.Request("https://html.duckduckgo.com/html/", data, {"User-Agent": UA})
        h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h, re.S)
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', h, re.S)
        res = []
        for i, (href, title) in enumerate(links[:8]):
            if "uddg=" in href:
                href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0]
            sn = strip_tags(snips[i]) if i < len(snips) else ""
            res.append(f"{i + 1}. {strip_tags(title)}\n{href}\n{sn}")
        if res:
            return "\n\n".join(res)
        print("DuckDuckGo 결과 없음", flush=True)
    except Exception as e:
        print("DuckDuckGo 실패", e, flush=True)
    if TAVILY:
        try:
            body = json.dumps({"query": q, "max_results": 6, "api_key": TAVILY}).encode()
            req = urllib.request.Request("https://api.tavily.com/search", body,
                                         {"Content-Type": "application/json", "Authorization": "Bearer " + TAVILY})
            r = json.load(urllib.request.urlopen(req, timeout=40))
            return "\n\n".join(f"{i + 1}. {x.get('title')}\n{x.get('url')}\n{(x.get('content') or '')[:300]}"
                               for i, x in enumerate(r.get("results", []))) or "검색 결과 없음"
        except Exception as e:
            print("Tavily 실패", e, flush=True)
    return "검색이 막혔어요. 검색어를 바꾸거나, 아는 주소를 fetch 하거나, shell에서 curl을 써 봐."

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=40).read(3000000).decode("utf-8", "ignore")
    return strip_tags(raw)[:6000] or "(글자 없음)"

def shell(cmd):
    p = subprocess.Popen(["bash", "-c", cmd], cwd=WS, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, errors="replace", env=ENV, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, 9)
        out, _ = p.communicate()
        out = (out or "") + "\n[5분 시간 초과로 멈춤]"
    return f"[종료코드 {p.returncode}]\n" + clip(out)

def write(path, body):
    path = path.strip().strip("'\"")
    for pre in (str(WS), "~/ws"):
        if path.startswith(pre):
            path = path[len(pre):]
    path = path.lstrip("/")
    if not path:
        return "ARG에 파일 경로를 써 줘."
    f = (WS / path).resolve()
    if not str(f).startswith(str(WS.resolve())):
        return "작업 폴더 밖에는 쓸 수 없어요."
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    return f"저장함: {path} ({len(body)}자)"

def esc(s):
    return html.escape(s or "")

def page(title, status, summary, steps, files):
    state = {"ok": "성공", "ask": "질문 필요", "fail": "미완료"}[status]
    pics = "".join(f'<img src="out/{urllib.parse.quote(f)}">' for f in files
                   if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")))
    flist = "".join(f'<li><a href="out/{urllib.parse.quote(f)}">{esc(f)}</a></li>' for f in files) or "<li>없음</li>"
    log = "".join(f'<details><summary>[{s["n"]}] {esc(s["act"])} {esc((s["arg"] or s["body"])[:100])}</summary>'
                  f'<pre>{esc(s["body"][:3000])}</pre><pre>{esc(s["obs"])}</pre></details>' for s in steps)
    return f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<style>body{{font-family:sans-serif;max-width:860px;margin:auto;padding:16px;line-height:1.6}}
pre{{background:#f4f4f4;padding:10px;overflow:auto;white-space:pre-wrap;font-size:13px}}img{{max-width:100%}}
details{{border-bottom:1px solid #ddd;padding:4px 0}}</style>
<p><a href="../">← 연구 목록</a></p><h1>{esc(title)}</h1>
<p>주제: {esc(TASK)}<br>결과: {state} · 행동 {len(steps)}번 · 모델 {esc(MODEL)}</p>
<h2>정리</h2><p>{esc(summary).replace(chr(10), "<br>")}</p>{pics}
<h2>결과 파일</h2><ul>{flist}</ul><h2>작업 기록</h2>{log}</html>"""

def index():
    items = []
    for m in pathlib.Path("docs").glob("*/meta.json"):
        try:
            items.append(json.loads(m.read_text(encoding="utf-8")))
        except Exception:
            pass
    items.sort(key=lambda x: x["id"], reverse=True)
    rows = "".join(f'<li><a href="{x["id"]}/">{esc(x["title"])}</a> · {x["id"]} · {"성공" if x["ok"] else "미완료"}</li>' for x in items)
    pathlib.Path("docs/index.html").write_text(f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>준봇 연구소</title>
<body style="font-family:sans-serif;max-width:860px;margin:auto;padding:16px"><h1>준봇 연구소</h1><ul>{rows}</ul></body></html>""", encoding="utf-8")

TOOLS = {"search", "fetch", "shell", "write", "done", "ask"}

def main():
    rid = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y%m%d-%H%M%S")
    d = pathlib.Path("docs", rid)
    (d / "out").mkdir(parents=True, exist_ok=True)
    (WS / "out").mkdir(parents=True, exist_ok=True)
    tg("🔬 연구 시작: " + TASK[:300])
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": "주제: " + TASK + "\n필요하면 먼저 검색해서 알아본 다음, 직접 실행하며 연구해. 첫 행동을 해."}]
    steps, title, summary, status, bad, start = [], "연구", "", "fail", 0, time.time()
    for n in range(1, MAX_STEPS + 1):
        if time.time() - start > LIMIT:
            print("시간 제한 도달", flush=True)
            break
        view = msgs if len(msgs) <= 32 else msgs[:2] + msgs[-30:]
        t = ask(view)
        act, arg, body = parse(t)
        if act not in TOOLS:
            bad += 1
            print(f"[{n}] 형식 오류", flush=True)
            msgs += [{"role": "assistant", "content": t or "(빈 답)"},
                     {"role": "user", "content": "형식을 지켜서 행동 하나만 다시 써. ACTION, ARG, BODY, END 순서."}]
            if bad >= 4:
                break
            continue
        bad = 0
        print(f"[{n}] {act} {(arg or body)[:100]!r}", flush=True)
        if act == "done":
            title, summary, status = arg or title, body.strip(), "ok"
            break
        if act == "ask":
            summary, status = arg or body.strip(), "ask"
            break
        try:
            obs = {"search": lambda: search(arg),
                   "fetch": lambda: fetch(arg),
                   "shell": lambda: shell(body or arg),
                   "write": lambda: write(arg, body)}[act]()
        except Exception as e:
            obs = f"오류: {e}"
        obs = clip(obs)
        steps.append({"n": n, "act": act, "arg": arg, "body": body, "obs": obs})
        note = "\n(남은 행동이 얼마 없어. 곧 마무리하고 done 해.)" if n >= MAX_STEPS - 3 else ""
        msgs += [{"role": "assistant", "content": t}, {"role": "user", "content": "결과:\n" + obs + note}]
    if not summary:
        log = "\n".join(f"[{s['n']}] {s['act']} {s['arg'] or s['body'][:200]}\n{s['obs'][:500]}" for s in steps[-15:])
        summary = ask([{"role": "user", "content": f"주제: {TASK}\n지금까지 한 일:\n{log}\n\n어디까지 했고 무엇이 막혔는지 한국어 평문으로 짧게 정리해 줘."}], 4000) or "정리 실패"
    files, total = [], 0
    for f in sorted((WS / "out").rglob("*")):
        if f.is_file() and f.stat().st_size < 20e6 and total < 50e6:
            rel = f.relative_to(WS / "out").as_posix()
            (d / "out" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d / "out" / rel)
            files.append(rel)
            total += f.stat().st_size
    (d / "index.html").write_text(page(title, status, summary, steps, files), encoding="utf-8")
    (d / "meta.json").write_text(json.dumps({"id": rid, "title": title, "ok": status == "ok", "task": TASK}, ensure_ascii=False), encoding="utf-8")
    if status == "ok":
        try:
            les = ask([{"role": "user", "content": f"연구: {title}\n{summary[:3000]}\n\n앞으로 코드를 짤 때 쓸 교훈을 한국어 한 줄로 써 줘. 언제 무엇을 쓰면 좋은지와 숫자를 넣어. 교훈이 없으면 없음이라고만 써."}], 4000).strip().splitlines()
            les = les[0].strip(" -*") if les else ""
            if les and not les.startswith("없음"):
                lp = pathlib.Path("docs/LESSONS.md")
                cur = lp.read_text(encoding="utf-8") if lp.exists() else "# 배운 점 노트 (연구소)\n"
                lp.write_text(cur.rstrip() + f"\n- {les} ({title})\n", encoding="utf-8")
        except Exception as e:
            print("교훈 실패", e, flush=True)
    index()
    link = SITE + rid + "/"
    if status == "ok":
        tg(f"✅ 연구 완료: {title}\n\n{summary[:1500]}\n\n보고서(1~2분 뒤 열림): {link}")
    elif status == "ask":
        tg(f"❓ 질문이 있어요: {summary[:1000]}\n\n답을 넣어서 다시 시켜 주세요.\n기록: {link}")
    else:
        tg(f"⚠️ 행동 {len(steps)}번 했지만 끝내지 못했어요.\n{summary[:1200]}\n\n기록: {link}")

if __name__ == "__main__":
    main()
