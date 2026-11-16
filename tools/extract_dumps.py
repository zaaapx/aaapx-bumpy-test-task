"""Pull Figma dump results out of the Claude session transcript into tools/dump/<id>.json.
Only used while building with Claude; normally paste the use_figma output into dump/ by hand."""
import json, sys, os
src = sys.argv[1]
out = os.path.join(os.path.dirname(__file__), 'dump')
n = 0
for line in open(src):
    try: rec = json.loads(line)
    except Exception: continue
    msg = rec.get('message') or {}
    content = msg.get('content')
    if not isinstance(content, list): continue
    for c in content:
        if c.get('type') != 'tool_result': continue
        body = c.get('content')
        texts = [b.get('text', '') for b in body] if isinstance(body, list) else [body or '']
        for t in texts:
            t = t.strip()
            if not t.startswith('[{"n":'): continue
            try: arr = json.loads(t)
            except Exception: continue
            for scr in arr:
                if 'id' in scr:
                    json.dump(scr, open(os.path.join(out, scr['id'].replace(':', '-') + '.json'), 'w'), ensure_ascii=False)
                    n += 1
print('screens', n, sorted(os.listdir(out)))
