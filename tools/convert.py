import sys, os, json, base64, math
import numpy as np

DL, OUT = sys.argv[1], sys.argv[2]
FPS = 30

def parse_bvh(path):
    with open(path, 'r', errors='replace') as f:
        text = f.read()
    head, motion = text.split('MOTION', 1)
    toks = head.split()
    names, parents, offsets, chans = [], [], [], []
    stack, i, cur = [], 0, -1
    while i < len(toks):
        t = toks[i]
        if t in ('ROOT', 'JOINT'):
            names.append(toks[i+1]); parents.append(stack[-1] if stack else -1)
            offsets.append([0, 0, 0]); chans.append([]); cur = len(names)-1; i += 2
        elif t == 'End':
            names.append(names[stack[-1]] + '_end'); parents.append(stack[-1])
            offsets.append([0, 0, 0]); chans.append([]); cur = len(names)-1; i += 2
        elif t == '{': stack.append(cur); i += 1
        elif t == '}': stack.pop(); i += 1
        elif t == 'OFFSET':
            offsets[stack[-1]] = [float(x) for x in toks[i+1:i+4]]; i += 4
        elif t == 'CHANNELS':
            n = int(toks[i+1]); chans[stack[-1]] = toks[i+2:i+2+n]; i += 2+n
        else: i += 1
    lines = motion.strip().split('\n')
    nfr = int(lines[0].split()[-1]); ft = float(lines[1].split()[-1])
    data = np.array([[float(x) for x in l.split()] for l in lines[2:2+nfr] if l.strip()], dtype=np.float64)
    return names, parents, np.array(offsets), chans, data, ft

def rot(axis, a):
    c, s = np.cos(a), np.sin(a); z, o = np.zeros_like(a), np.ones_like(a)
    if axis == 'X': m = [[o, z, z], [z, c, -s], [z, s, c]]
    elif axis == 'Y': m = [[c, z, s], [z, o, z], [-s, z, c]]
    else: m = [[c, -s, z], [s, c, z], [z, z, o]]
    return np.stack([np.stack(r, -1) for r in m], -2)

def fk(names, parents, offsets, chans, data):
    F = data.shape[0]; J = len(names)
    pos = np.zeros((F, J, 3)); R = np.zeros((F, J, 3, 3)); col = 0
    for j in range(J):
        Rl = np.tile(np.eye(3), (F, 1, 1)); t = np.tile(offsets[j], (F, 1))
        tp = np.zeros((F, 3)); has_t = False
        for ch in chans[j]:
            v = data[:, col]; col += 1
            if ch.endswith('position'):
                tp[:, 'XYZ'.index(ch[0])] = v; has_t = True
            else:
                Rl = Rl @ rot(ch[0], np.radians(v))
        if has_t: t = tp if parents[j] < 0 else t + tp
        p = parents[j]
        if p < 0: pos[:, j] = t; R[:, j] = Rl
        else:
            pos[:, j] = pos[:, p] + np.einsum('fij,fj->fi', R[:, p], t); R[:, j] = R[:, p] @ Rl
    return pos, R

def gauss(x, sigma):
    r = int(max(1, round(sigma*3))); k = np.exp(-0.5*(np.arange(-r, r+1)/sigma)**2); k /= k.sum()
    if x.ndim == 1: return np.convolve(np.pad(x, r, mode='edge'), k, mode='valid')
    return np.stack([gauss(x[:, i], sigma) for i in range(x.shape[1])], 1)

def idx(names, *cands):
    low = [n.lower() for n in names]
    for c in cands:
        if c.lower() in low: return low.index(c.lower())
    raise KeyError(cands)

def side_of(n):
    if n.startswith('Left') or (n[0] == 'L' and len(n) > 1 and n[1].isupper()): return 1
    if n.startswith('Right') or (n[0] == 'R' and len(n) > 1 and n[1].isupper()): return 2
    return 0

def radius(pn, cn, ds):
    p = pn.lower(); c = cn.lower()
    if 'head' in p: return -1.0
    if 'toe' in p: return .028
    if 'foot' in p or 'ankle' in p: return .036
    if 'upleg' in p or (ds == 'style' and p.endswith('hip')): return .062
    if p.endswith('leg') or 'knee' in p: return .048
    if p == 'hips' or 'hipjoint' in p:
        return .085 if ('spine' in c or 'chest' in c or 'lowerback' in c) else .07
    if 'neck' in p: return .042
    if 'chest' in p or 'spine' in p or 'lowerback' in p:
        return .085 if ('chest' in c or 'spine' in c or 'neck' in c) else .05
    if 'collar' in p: return .046
    if 'forearm' in p or 'elbow' in p: return .035
    if ds == 'style' and p.endswith('shoulder'): return .042
    if p.endswith('shoulder'): return .046
    if p.endswith('arm'): return .042
    return .024

def runs(mask):
    out = []; s = None
    for i, m in enumerate(mask):
        if m and s is None: s = i
        if not m and s is not None: out.append([s, i]); s = None
    if s is not None: out.append([s, len(mask)])
    return out

def contacts(p, floor):
    v = np.linalg.norm(np.diff(p, axis=0, prepend=p[:1]), axis=1)*FPS
    v = gauss(v, 1.0)
    c = (v < 0.45) & (p[:, 1] < floor + 0.09)
    r = runs(c); merged = []
    for a, b in r:
        if merged and a - merged[-1][1] <= 3: merged[-1][1] = b
        else: merged.append([a, b])
    return [[a, b] for a, b in merged if b - a >= 4]

def process(spec):
    ds = spec['ds']
    names, parents, offsets, chans, data, ft = parse_bvh(os.path.join(DL, spec['file']))
    he, hj = names.index('Head_end'), names.index('Head')
    if np.linalg.norm(offsets[he]) < 1e-6:  # no head tip recorded: continue the neck bone's axis
        offsets[he] = offsets[hj]*1.5
    for hn in ('LeftHand', 'RightHand'):  # same for a hand with no recorded tip: about 8 cm along the hand's own axis
        if hn in names and hn + '_end' in names and np.linalg.norm(offsets[names.index(hn + '_end')]) < 1e-6:
            offsets[names.index(hn + '_end')] = offsets[names.index(hn)]*0.32
    step = max(1, int(round((1.0/ft)/FPS)))
    data = data[1::step]
    pos, Rg = fk(names, parents, offsets, chans, data)
    if ds == 'style':
        hipL, hipR, knee, ank = idx(names, 'LeftHip'), idx(names, 'RightHip'), idx(names, 'LeftKnee'), idx(names, 'LeftAnkle')
        ankR, hand = idx(names, 'RightAnkle'), idx(names, 'RightWrist')
    else:
        hipL, hipR, knee, ank = idx(names, 'LeftUpLeg'), idx(names, 'RightUpLeg'), idx(names, 'LeftLeg'), idx(names, 'LeftFoot')
        ankR, hand = idx(names, 'RightFoot'), idx(names, 'RightHand')
    head = idx(names, 'Head'); headEnd = idx(names, 'Head_end')
    leg = np.linalg.norm(offsets[knee]) + np.linalg.norm(offsets[ank])
    pos *= 0.88/leg
    r0 = pos[:, hipR] - pos[:, hipL]
    fb = np.stack([r0[:, 2], np.zeros(len(r0)), -r0[:, 0]], 1); fb /= np.linalg.norm(fb, axis=1, keepdims=True) + 1e-9
    vl = np.einsum('fji,fj->fi', Rg[:, head], fb).mean(axis=0)
    ul = offsets[headEnd]/(np.linalg.norm(offsets[headEnd]) + 1e-9)  # the head's own up axis
    vl -= ul*vl.dot(ul); vl /= np.linalg.norm(vl) + 1e-9             # face direction is square to it
    nose = (pos[:, head] + pos[:, headEnd])/2 + np.einsum('fij,j->fi', Rg[:, head], vl)*0.1
    pos = np.concatenate([pos, nose[:, None, :]], 1)
    names = names + ['Nose']; parents = parents + [head]
    floor = np.percentile(pos[:, :, 1].min(axis=1), 2) - 0.03
    pos[:, :, 1] -= floor
    F = pos.shape[0]
    root = pos[:, 0, [0, 2]]
    rs = gauss(root, 0.4*FPS)
    r = pos[:, hipR] - pos[:, hipL]
    fx, fz = r[:, 2], -r[:, 0]
    h = np.unwrap(np.arctan2(-fz, fx)); hs = gauss(h, 0.5*FPS)
    v = np.linalg.norm(np.diff(rs, axis=0, prepend=rs[:1]), axis=1)*FPS
    w = np.abs(np.diff(hs, prepend=hs[:1]))*FPS
    W = int(spec.get('win', 14)*FPS); margin = int(spec.get('margin', 4)*FPS)
    if F <= W + 2*margin:
        a, b = min(15, F//10), F - min(15, F//10)
    else:
        best, a = -1e9, margin
        for s in range(margin, F - W - margin, 15):
            vv, ww = v[s:s+W], w[s:s+W]
            mode = spec.get('mode', 'walk')
            if mode == 'walk': sc = vv.mean() - 0.6*ww.mean() - 2.0*(vv < 0.25).mean()
            elif mode == 'startstop': sc = vv.std() - 0.3*ww.mean()
            else: sc = ((vv > 0.5) & (vv < 2.2)).mean() - 0.1*ww.mean()
            if sc > best: best, a = sc, s
        b = a + W
    pos, rs, hs, v = pos[a:b], rs[a:b], hs[a:b], v[a:b]
    F = pos.shape[0]
    ch, sh = np.cos(hs)[:, None], np.sin(hs)[:, None]
    dx, dz = pos[:, :, 0] - rs[:, None, 0], pos[:, :, 2] - rs[:, None, 1]
    loc = np.stack([dx*ch - dz*sh, pos[:, :, 1], dx*sh + dz*ch], -1)
    world = pos
    fl = min(np.percentile(world[:, ank, 1], 5), np.percentile(world[:, ankR, 1], 5))
    cL, cR = contacts(world[:, ank], fl), contacts(world[:, ankR], fl)
    dist = float(np.linalg.norm(np.diff(rs, axis=0), axis=1).sum()); T = F/FPS
    steps = len(cL) + len(cR)
    rad = [0.0]*len(names); side = [0]*len(names)
    for j, n in enumerate(names):
        if n == 'Nose': rad[j] = -2.0
        elif parents[j] >= 0:
            rad[j] = radius(names[parents[j]], n, ds); side[j] = side_of(n) or side_of(names[parents[j]])
    q = np.clip(np.round(loc*1000), -32000, 32000).astype('<i2')
    rootf = np.concatenate([rs, hs[:, None]], 1).astype('<f4')
    return dict(id=spec['id'], group=spec['group'], label=spec['label'], source=spec['source'], n=F, fps=FPS,
        names=names, parents=parents, rad=rad, side=side, head=head, headEnd=headEnd, hand=hand,
        pos=base64.b64encode(q.tobytes()).decode(), root=base64.b64encode(rootf.tobytes()).decode(),
        contacts=dict(L=cL, R=cR),
        metrics=dict(speed=round(dist/T*3.6, 1), cadence=round(steps/T*60) if steps else 0,
                     step=round(dist/steps*100) if steps else 0, dist=round(dist, 1), secs=round(T, 1), src_start=round(a/FPS, 1)))

S100 = '100STYLE (Ian Mason), CC BY 4.0'; CMU = 'CMU Graphics Lab Motion Capture Database'; LAF = 'Ubisoft La Forge LAFAN1, CC BY-NC-ND 4.0'
def st(g, n, label, **k): return dict(id='s_'+n.lower(), group=g, ds='style', file='style/%s_FW.bvh' % n, label=label, source=S100+', style "%s"' % n, **k)
def cm(g, n, label, **k): return dict(id='c_'+n, group=g, ds='cmu', file='cmu/%s.bvh' % n, label=label, source=CMU+', clip %s' % n, **k)
def la(g, n, label, **k): return dict(id='l_'+n, group=g, ds='lafan', file='lafan/%s.bvh' % n, label=label, source=LAF+', %s' % n, mode='aim', **k)
SPECS = [
  st('baseline', 'Neutral', 'Neutral walk'), cm('baseline', '137_29', 'Normal walk'),
  st('elderly', 'Old', 'Old'), cm('elderly', '137_33', 'Old man walk'), cm('elderly', '142_07', 'Elderly man'), st('elderly', 'WalkingStickLeft', 'With a walking stick'),
  cm('young', '137_20', 'Gangly teen'), cm('young', '132_29', 'Bouncy walk'), st('young', 'Elated', 'Elated'), st('young', 'Strutting', 'Strutting'),
  la('operator', 'aiming1_subject1', 'Moving with a weapon, actor 1'), la('operator', 'aiming2_subject3', 'Moving with a weapon, actor 2'),
  st('operator', 'Swat', 'SWAT style'), st('operator', 'Crouched', 'Crouched'), cm('operator', '77_25', 'Careful walk and search'), cm('operator', '139_29', 'Sneaking'),
  st('erratic', 'Drunk', 'Drunk'), cm('erratic', '137_16', 'Drunk walk'), st('erratic', 'Angry', 'Angry'), st('erratic', 'StartStop', 'Start and stop', mode='startstop'),
  st('erratic', 'Followed', 'Being followed'), cm('erratic', '142_16', 'Scared'), cm('erratic', '105_32', 'Scared, second actor'),
]
# Usage: python3 convert.py <download folder> <clips.json>
# The Ubisoft takes are CC BY-NC-ND, so they are written to clips.ubisoft.json beside it and kept out of the repository.
clips, ubisoft = [], []
for s in SPECS:
    if not os.path.exists(os.path.join(DL, s['file'])):
        print('SKIP', s['id'], '(source file not downloaded)'); continue
    try:
        c = process(s); (ubisoft if s['ds'] == 'lafan' else clips).append(c)
        m = c['metrics']; print('%-22s %-9s frames=%4d joints=%2d from=%6.1fs speed=%4.1f km/h cadence=%3d step=%3d cm L/R contacts=%d/%d' % (
            c['id'], c['group'], c['n'], len(c['names']), m['src_start'], m['speed'], m['cadence'], m['step'], len(c['contacts']['L']), len(c['contacts']['R'])))
    except Exception as e:
        print('FAIL', s['id'], repr(e))
with open(OUT, 'w') as f: json.dump(dict(clips=clips), f, separators=(',', ':'))
print('wrote', OUT, os.path.getsize(OUT), len(clips), 'clips')
if ubisoft:
    OUT2 = os.path.join(os.path.dirname(os.path.abspath(OUT)), 'clips.ubisoft.json')
    with open(OUT2, 'w') as f: json.dump(dict(clips=ubisoft), f, separators=(',', ':'))
    print('wrote', OUT2, os.path.getsize(OUT2), len(ubisoft), 'clips (do not publish)')
