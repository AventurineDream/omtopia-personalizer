#!/usr/bin/python3 -I
"""Точка входа бэкенда Customizer.

  run.py serve            постоянный режим для overlay (JSON-строки по stdin/stdout)
  run.py <команда> …      как customizer.sh <команда> …

Запускается системным /usr/bin/python3 с -I (mise-python без нужных модулей не подхватится);
-I не кладёт каталог скрипта в sys.path — добавляем сами."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from customizer import commands, paths, serve  # noqa: E402


def main():
    args = sys.argv[1:]
    if args[:1] == ["serve"]:
        serve.main()
        return 0
    if not commands.handled_here(args):
        # Ещё не перенесено — сразу старый bash, без лишнего круга через subprocess.
        os.environ["CUSTOMIZER_LEGACY"] = "1"
        os.execv("/bin/bash", ["bash", str(paths.LEGACY), *args])
    code, out, err = commands.run(args)
    sys.stdout.write(out)
    sys.stderr.write(err)
    return code


if __name__ == "__main__":
    sys.exit(main())
