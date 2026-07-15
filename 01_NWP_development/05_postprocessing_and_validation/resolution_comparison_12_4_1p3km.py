import glob, os, numpy as np, pandas as pd
from netCDF4 import Dataset
from scipy.spatial import cKDTree
import warnings; warnings.filterwarnings("ignore")

D="/Users/haseeb.rehman/Documents/Misc/From_HPC_and_WRF/WRF_Local_machine/4th_year/2021_ERA5_local_machine_3_domains/After_DA"
OBS="/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Stations_and_Observations/Luxembourg_stations_for_validation/2021_Event/stations_6hr_cumulative.xlsx"

# 17 stations inside all three domains AND in observed file (Briedfeld excluded: outside d03)
stations=[("Echternach",49.80310,6.44337),("Ettelbruck",49.85172,6.09754),("Oberkorn",49.51220,5.90110),
("Remerschen",49.49100,6.34900),("Roodt",49.79450,5.82020),("Hosingen",49.99314,6.10147),
("Useldange",49.76739,5.96748),("Mamer",49.63353,6.01930),("Arsdorf",49.85891,5.84868),
("Asselborn",50.09686,5.96961),("Grevenmacher",49.68087,6.43541),("Schimpach",50.00930,5.84750),
("Waldbillig",49.79806,6.27730),("Bettendorf",49.87410,6.20950),("Fouhren",49.91445,6.19508),
("Beringen",49.76200,6.11179),("Dahl",49.93595,5.98093)]

def extract(dom):
    files=sorted(glob.glob(os.path.join(D,f"wrfout_{dom}_*")))
    rows={s[0]:[] for s in stations}
    tree=None
    for f in files:
        nc=Dataset(f)
        xlat=nc.variables['XLAT'][0]; xlon=nc.variables['XLONG'][0]
        if tree is None:
            tree=cKDTree(np.column_stack((xlat.ravel(),xlon.ravel()))); shp=xlat.shape
        t2=nc.variables['T2'][0]; rnc=nc.variables['RAINNC'][0]; rc=nc.variables['RAINC'][0]
        rsh=nc.variables['RAINSH'][0] if 'RAINSH' in nc.variables else np.zeros_like(rnc)
        bn=os.path.basename(f).split("_"); dt=pd.to_datetime(f"{bn[2]} {bn[3]}:{bn[4]}:{bn[5]}")
        for name,lat,lon in stations:
            _,idx=tree.query([lat,lon]); i,j=np.unravel_index(idx,shp)
            rows[name].append({"UTC_Datetime":dt,"Sim_P":float(rnc[i,j]+rc[i,j]+rsh[i,j]),"Sim_T":float(t2[i,j]-273.15)})
        nc.close()
    return {k:pd.DataFrame(v) for k,v in rows.items()}

def metrics(sim,obs):
    d=pd.concat([sim,obs],axis=1).dropna()
    if len(d)<2: return None
    return d

def agg(dom_data):
    P=[];T=[];POD=[];FAR=[]
    for name,lat,lon in stations:
        try: dfo=pd.read_excel(OBS,sheet_name=name)
        except: continue
        dfo['UTC_Datetime']=pd.to_datetime(dfo['UTC_Datetime'])
        dfo=dfo.rename(columns={'Precip(mm)':'Obs_P','Temp(2m)':'Obs_T'})[['UTC_Datetime','Obs_P','Obs_T']]
        m=pd.merge(dom_data[name],dfo,on='UTC_Datetime',how='inner').dropna()
        if len(m)<2: continue
        # precip
        sp,op=m['Sim_P'],m['Obs_P']
        rmse=np.sqrt(np.mean((sp-op)**2)); mae=np.mean(np.abs(sp-op)); bias=np.mean(sp-op)
        den=(np.abs(sp)+np.abs(op))/2; nz=den!=0
        smape=np.mean(np.abs(sp-op)[nz]/den[nz])*100 if nz.any() else np.nan
        P.append((rmse,mae,smape,bias))
        thr=0.1; oz=op>thr; sz=sp>thr
        hits=(sz&oz).sum(); miss=((~sz)&oz).sum(); fa=(sz&(~oz)).sum()
        pod=hits/(hits+miss) if (hits+miss)>0 else np.nan
        far=fa/(hits+fa) if (hits+fa)>0 else np.nan
        POD.append(pod); FAR.append(far)
        # temp
        st,ot=m['Sim_T'],m['Obs_T']
        rmse=np.sqrt(np.mean((st-ot)**2)); mae=np.mean(np.abs(st-ot)); bias=np.mean(st-ot)
        den=(np.abs(st)+np.abs(ot))/2; nz=den!=0
        smape=np.mean(np.abs(st-ot)[nz]/den[nz])*100 if nz.any() else np.nan
        r=np.corrcoef(st,ot)[0,1]
        T.append((rmse,mae,smape,bias,r))
    P=np.array(P); T=np.array(T)
    return {
        'n_stations':len(P),
        'P_RMSE':np.nanmean(P[:,0]),'P_MAE':np.nanmean(P[:,1]),'P_SMAPE':np.nanmean(P[:,2]),'P_Bias':np.nanmean(P[:,3]),
        'POD':np.nanmean(POD),'FAR':np.nanmean(FAR),
        'T_RMSE':np.nanmean(T[:,0]),'T_MAE':np.nanmean(T[:,1]),'T_SMAPE':np.nanmean(T[:,2]),'T_Bias':np.nanmean(T[:,3]),'T_Corr':np.nanmean(T[:,4])
    }

results={}
for dom,label in [('d01','12 km'),('d02','4 km'),('d03','1.3 km')]:
    print(f"extracting {dom} ({label})...")
    dd=extract(dom); results[label]=agg(dd)

print("\n=== RESOLUTION COMPARISON (After-DA, ERA5, July 2021, %d stations) ==="%results['12 km']['n_stations'])
print("\nPRECIPITATION:")
print(f"{'Resolution':<10}{'RMSE':>8}{'MAE':>8}{'SMAPE':>8}{'Bias':>8}{'POD':>8}{'FAR':>8}")
for label in ['12 km','4 km','1.3 km']:
    r=results[label]
    print(f"{label:<10}{r['P_RMSE']:>8.3f}{r['P_MAE']:>8.3f}{r['P_SMAPE']:>8.2f}{r['P_Bias']:>8.3f}{r['POD']:>8.3f}{r['FAR']:>8.3f}")
print("\nTEMPERATURE:")
print(f"{'Resolution':<10}{'RMSE':>8}{'MAE':>8}{'SMAPE':>8}{'Bias':>8}{'Corr':>8}")
for label in ['12 km','4 km','1.3 km']:
    r=results[label]
    print(f"{label:<10}{r['T_RMSE']:>8.3f}{r['T_MAE']:>8.3f}{r['T_SMAPE']:>8.2f}{r['T_Bias']:>8.3f}{r['T_Corr']:>8.3f}")

import json
json.dump(results,open('/tmp/resolution_results.json','w'),indent=2)
print("\nsaved /tmp/resolution_results.json")
