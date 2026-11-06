"""Постоянный режим для overlay: запрос и ответ — по строке JSON.

  → {"id": 1, "cmd": ["list", "bar-tweaks"]}
  ← {"id": 1, "code": 0, "out": "<TSV>", "err": ""}

Живёт, пока открыт Customizer: overlay закрывает stdin — цикл кончается, процесс выходит.
В простое процесс спит в read() — ни таймеров, ни опроса. Кэш settings.json и переводов
держится между запросами (поэтому быстрее отдельных запусков)."""
import json
import sys

from . import commands


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            args = [str(a) for a in req.get("cmd", [])]
            code, out, err = commands.run(args)
        except Exception as e:  # ответ должен прийти всегда, иначе overlay ждёт вечно
            req = req if isinstance(locals().get("req"), dict) else {}
            code, out, err = 1, "", f"{type(e).__name__}: {e}"
        sys.stdout.write(json.dumps({"id": req.get("id"), "code": code, "out": out, "err": err}, ensure_ascii=False) + "\n")
        sys.stdout.flush()
