"""localStorage 덤프 -> 7장 스키마.

실제 세이브 구조는 아직 확인되지 않았다. 그래서 2단계로 나눈다.
  1) inspect: 덤프의 키/구조만 출력 (값은 짧게 자름)
  2) convert: 사람이 inspect 결과를 보고 쓴 매핑 파일로 변환

사용:
  python3 scripts/ingest.py inspect data/raw/dump.json
  python3 scripts/ingest.py convert data/raw/dump.json mapping.json data/out/char.json

덤프 형식 (SKILL.md가 만든다):
  {"origin": "...", "dumped_at": "...", "keys": {"<localStorage 키>": "<원문 문자열>"}}

mapping.json 예:
  {
    "key": "<세이브가 든 localStorage 키>",
    "seasons_path": "career.seasons",
    "character": {"character_id": "me", "position": "ST", "nationality": null},
    "fields": {"season": "label", "goals": "stats.goals", "ballon_rank": "ballon.rank"},
    "value_maps": {"ballon_status": {"WON": "won", "NC": "not_candidate"}}
  }
fields 에 없는 스키마 필드는 null 이 된다 (0 으로 채우지 않는다).
"""
import json
import sys

from common import SEASON_KEYS, die, load

MAX_DEPTH = 4
MAX_ITEMS = 12


def parse_value(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    return raw


def describe(v, depth=0):
    pad = "  " * (depth + 1)
    if isinstance(v, dict):
        if depth >= MAX_DEPTH:
            return f"dict({len(v)} keys)"
        lines = [f"dict({len(v)} keys)"]
        for k in list(v)[:MAX_ITEMS]:
            lines.append(f"{pad}{k}: {describe(v[k], depth + 1)}")
        if len(v) > MAX_ITEMS:
            lines.append(f"{pad}... +{len(v) - MAX_ITEMS} keys")
        return "\n".join(lines)
    if isinstance(v, list):
        if not v or depth >= MAX_DEPTH:
            return f"list({len(v)})"
        return f"list({len(v)}) of " + describe(v[0], depth + 1)
    if isinstance(v, str):
        return f"str {v[:30]!r}" + ("..." if len(v) > 30 else "")
    return f"{type(v).__name__} {v!r}"


def inspect(path):
    dump = load(path)
    keys = dump.get("keys")
    if not isinstance(keys, dict):
        die("덤프에 keys 객체가 없음")
    print(f"origin={dump.get('origin')} dumped_at={dump.get('dumped_at')} 키 {len(keys)}개")
    for k, raw in keys.items():
        size = len(raw) if isinstance(raw, str) else 0
        print(f"\n- {k}  ({size} chars)\n  {describe(parse_value(raw), 1)}")


def get_path(obj, path):
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list) and part.isdigit() and int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return None
    return obj


def convert(dump_path, mapping_path, out_path):
    dump, m = load(dump_path), load(mapping_path)
    raw = dump["keys"].get(m["key"])
    if raw is None:
        die(f"덤프에 키 {m['key']!r} 없음")
    seasons_raw = get_path(parse_value(raw), m["seasons_path"])
    if not isinstance(seasons_raw, list):
        die(f"seasons_path {m['seasons_path']!r} 가 list 가 아님")

    maps = m.get("value_maps", {})
    source = f"dump:{dump.get('origin')}:{dump.get('dumped_at')}"
    seasons = []
    for item in seasons_raw:
        s = {k: None for k in SEASON_KEYS}
        for field, path in m["fields"].items():
            if field not in s:
                die(f"스키마에 없는 필드 {field!r}")
            val = get_path(item, path)
            if field in maps and val is not None:
                val = maps[field].get(val, val)
            s[field] = val
        s["note"] = s["note"] or ""
        s["source"] = source
        if s["ballon_status"] is None:
            s["ballon_status"] = "unknown"
        seasons.append(s)

    out = dict(m.get("character", {}), seasons=seasons)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{len(seasons)}시즌 -> {out_path}  (이어서 validate.py 실행)")


def main(argv):
    if len(argv) == 2 and argv[0] == "inspect":
        inspect(argv[1])
    elif len(argv) == 4 and argv[0] == "convert":
        convert(*argv[1:])
    else:
        die(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
