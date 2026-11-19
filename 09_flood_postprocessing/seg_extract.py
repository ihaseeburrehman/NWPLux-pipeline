"""Integrate q.n over precomputed transect segments for any width/offset. Used locally and on HPC."""
# Helper module imported by xs_fullvalley.py; it has no command line.
# Transect file: JSON with, per station, the unit normal (ux, uy) and segments [row, col, start, end] (m along the line).
# The grid size defaults in read_rows (4362 x 2440) must match the 10 m DEM.
import json, numpy as np
def load(path): return json.load(open(path))
# Sorted list of grid rows touched by any segment
def rows_needed(T):
    return sorted({s[0] for v in T.values() for s in v['segs']})
# Read only the needed rows of an .asc grid (the 6 header lines are skipped)
def read_rows(path, need, nrows=4362, ncols=2440):
    need=set(need); out={}
    with open(path) as f:
        for _ in range(6): f.readline()
        for i,line in enumerate(f):
            if i in need: out[i]=np.array(line.split(),dtype=np.float32)
    return out
def seg_flux(T, QX, QY, WD=None):
    """per station: arrays t_mid, length, q.n (m2/s), depth"""
    res={}
    for n,v in T.items():
        tm=[];L=[];qn=[];d=[]
        for rr,cc,a,b in v['segs']:
            # Flux normal to the section (nodata -9999 -> 0) and depth at the segment's cell
            qx=QX[rr][cc]; qy=QY[rr][cc]
            tm.append((a+b)/2); L.append(b-a); qn.append(0.0 if qx==-9999 or qy==-9999 else qx*v['ux']+qy*v['uy'])
            d.append(np.nan if WD is None else WD[rr][cc])
        res[n]=dict(t=np.array(tm),L=np.array(L),qn=np.array(qn),wd=np.array(d))
    return res
def Q(r, a, b):
    """exact integral of q.n over t in [a,b]"""
    t,L,qn=r['t'],r['L'],r['qn']; lo=t-L/2; hi=t+L/2
    ov=np.clip(np.minimum(hi,b)-np.maximum(lo,a),0,None)
    return float((qn*ov).sum())
