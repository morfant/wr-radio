"""Minimal KiCad s-expression parser / serializer + symbol library helpers."""
import copy
import re

SYMDIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    stack = [[]]
    for t in tokens:
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop()
            stack[-1].append(x)
        elif t.startswith('"'):
            stack[-1].append(re.sub(r'\\(.)', lambda m: '\n' if m.group(1) == 'n' else m.group(1), t[1:-1]))
        elif re.fullmatch(r'-?\d+(\.\d+)?', t):
            stack[-1].append(float(t))
        else:
            stack[-1].append(Sym(t))
    return stack[0][0]


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def dump(x, ind=0):
    if isinstance(x, list):
        # short lists on one line
        if all(not isinstance(e, list) for e in x):
            return '\t' * ind + '(' + ' '.join(atom(e) for e in x) + ')'
        head = []
        rest = []
        i = 0
        while i < len(x) and not isinstance(x[i], list):
            head.append(atom(x[i]))
            i += 1
        out = '\t' * ind + '(' + ' '.join(head)
        for e in x[i:]:
            if isinstance(e, list):
                out += '\n' + dump(e, ind + 1)
            else:
                out += ' ' + atom(e)
        out += '\n' + '\t' * ind + ')'
        return out
    return '\t' * ind + atom(x)


def atom(e):
    if isinstance(e, Sym):
        return str(e)
    if isinstance(e, bool):
        return 'yes' if e else 'no'
    if isinstance(e, (int, float)):
        return fmtnum(e)
    return q(e)


def fmtnum(v):
    v = round(float(v), 6)
    if v == int(v):
        return str(int(v))
    return ('%.6f' % v).rstrip('0').rstrip('.')


def find(lst, key):
    for e in lst:
        if isinstance(e, list) and e and e[0] == key:
            return e
    return None


def findall(lst, key):
    return [e for e in lst if isinstance(e, list) and e and e[0] == key]


_libcache = {}


def load_lib(name, path=None):
    if name not in _libcache:
        p = path or f"{SYMDIR}/{name}.kicad_sym"
        _libcache[name] = parse(open(p, encoding='utf-8').read())
    return _libcache[name]


def get_symbol(lib, name, libpath=None):
    L = load_lib(lib, libpath)
    for s in findall(L, 'symbol'):
        if s[1] == name:
            return copy.deepcopy(s)
    raise KeyError(f"{lib}:{name}")


def flatten(lib, name, libpath=None):
    """Return a flattened symbol (no extends) named `name` (no lib prefix)."""
    s = get_symbol(lib, name, libpath)
    ext = find(s, 'extends')
    if not ext:
        return s
    parent = flatten(lib, ext[1], libpath)
    pname = parent[1]
    # child props override parent props
    cprops = {p[1]: p for p in findall(s, 'property')}
    out = [Sym('symbol'), name]
    for e in parent[2:]:
        if isinstance(e, list) and e[0] == 'property':
            if e[1] in cprops:
                out.append(cprops.pop(e[1]))
            else:
                out.append(e)
        elif isinstance(e, list) and e[0] == 'symbol':
            sub = copy.deepcopy(e)
            assert sub[1].startswith(pname + '_'), sub[1]
            sub[1] = name + sub[1][len(pname):]
            out.append(sub)
        else:
            out.append(e)
    # remaining child-only properties: insert after last property
    idx = max(i for i, e in enumerate(out) if isinstance(e, list) and e[0] == 'property')
    for p in cprops.values():
        idx += 1
        out.insert(idx, p)
    return out


def pins_of(sym):
    """List of dicts: number, name, x, y, rot, length, type, unit, hidden."""
    res = []
    for sub in findall(sym, 'symbol'):
        m = re.match(r'.*_(\d+)_(\d+)$', sub[1])
        unit, style = int(m.group(1)), int(m.group(2))
        if style not in (0, 1):
            continue
        for p in findall(sub, 'pin'):
            at = find(p, 'at')
            res.append(dict(
                number=find(p, 'number')[1], name=find(p, 'name')[1],
                x=float(at[1]), y=float(at[2]), rot=float(at[3]) if len(at) > 3 else 0.0,
                length=float(find(p, 'length')[1]), type=str(p[1]), unit=unit,
                hidden=any(e == 'hide' or (isinstance(e, list) and e[0] == 'hide' and e[1] == 'yes') for e in p)))
    return res
