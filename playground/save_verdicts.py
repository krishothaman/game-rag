import json
import re
import sys
from pathlib import Path

from game_rag import config

# usage: save_verdicts.py answers.txt [--holdout] 1=y 3=n ...
src = Path(sys.argv[1])
path = config.HOLDOUT_VERDICTS_FILE if "--holdout" in sys.argv else config.VERDICTS_FILE
mine = {int(k): v == "y" for k, v in (a.split("=") for a in sys.argv[2:] if "=" in a)}
verdicts = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
qid, saved = None, 0
for line in src.read_text(encoding="utf-8").splitlines():
    m = re.match(r"=== #(\d+) ", line)
    if m:
        qid = int(m.group(1))
    elif line.startswith("ANSWER: ") and qid in mine:
        verdicts[f"{qid}|{line[8:]}"] = mine[qid]
        saved += 1
path.write_text(json.dumps(verdicts, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"saved {saved} verdicts to {path.name}")
