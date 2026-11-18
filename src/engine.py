from __future__ import annotations
import argparse, json, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mean_absolute_error, brier_score_loss, log_loss, roc_auc_score

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data"/"raw"; PROC=ROOT/"data"/"processed"; OUT=ROOT/"outputs"; MODELS=ROOT/"models"
for p in [PROC,OUT,MODELS]: p.mkdir(parents=True,exist_ok=True)
SEED=42
THRESHOLDS={
 "relaxed":{"pressure_matches":5,"normal_matches":5,"pressure_balls":40,"normal_balls":75},
 "current":{"pressure_matches":8,"normal_matches":8,"pressure_balls":60,"normal_balls":100},
 "strict":{"pressure_matches":12,"normal_matches":12,"pressure_balls":100,"normal_balls":150},
}
HDPI_W={"msd":.25,"wpl":.30,"rsi":.20,"ssi":.15,"pep":.10}
BPI_W={"hdpi":.35,"urgency":.25,"dismissal":.20,"responsibility":.20}
BOPI_W={"hdpi":.35,"defence":.25,"wicket":.20,"responsibility":.20}

def read_inputs():
    required=["ball_by_ball.csv","matches.csv","competitions.csv"]
    missing=[x for x in required if not (RAW/x).exists()]
    if missing: raise FileNotFoundError(f"Missing raw input files in data/raw: {missing}")
    b=pd.read_csv(RAW/"ball_by_ball.csv",low_memory=False)
    m=pd.read_csv(RAW/"matches.csv",low_memory=False)
    c=pd.read_csv(RAW/"competitions.csv",low_memory=False)
    return b,m,c

def phase1():
    b,m,c=read_inputs()
    b["delivery_ist_time"]=pd.to_datetime(b["delivery_ist_time"],errors="coerce",utc=True)
    # Match date is authoritative for season chronology; delivery time is retained.
    m["match_date"]=pd.to_datetime(m["match_date"],errors="coerce")
    x=b.merge(m[["match_id","comp_id","match_date","first_inn_revised_overs",
                 "second_inn_revised_overs","revised_target","win_team_id","home_team_id",
                 "away_team_id","result"]],on="match_id",how="left",validate="many_to_one")
    x=x.merge(c[["comp_id","match_format","season"]],on="comp_id",how="left",validate="many_to_one")
    x["season"]=pd.to_numeric(x["season"],errors="coerce").fillna(x["match_date"].dt.year).astype(int)
    x["match_format"]=x["match_format"].fillna("Unknown")
    x["innings"]=pd.to_numeric(x["innings"],errors="coerce").fillna(0).astype(int)
    x=x[x["innings"].isin([1,2])].copy()  # exclude Super Overs / extra innings
    for col in ["runs","extras1_runs","extras_2_runs","is_wicket"]:
        x[col]=pd.to_numeric(x[col],errors="coerce").fillna(0)
    et=x["extras_type"].fillna("").astype(str).str.lower()
    x["is_wide"]=et.eq("wide")
    x["is_noball"]=et.eq("overstep")
    x["is_legal_ball"]=~(x["is_wide"]|x["is_noball"])
    x["team_runs"]=x["runs"]+x["extras1_runs"]+x["extras_2_runs"]
    x["bowler_runs_conceded"]=x["runs"]+np.where(x["is_wide"]|x["is_noball"],x["extras1_runs"]+x["extras_2_runs"],0)
    # A batter is credited with a ball faced on every delivery except a wide.
    x["batter_ball_faced"]=~x["is_wide"]
    credited=["Caught","Bowled","LBW","Stump","Hit Wicket"]
    x["bowler_wicket"]=x["dismissal_type"].isin(credited).astype(int)
    x["match_date"]=pd.to_datetime(x["match_date"],errors="coerce")
    x=x.sort_values(["match_date","match_id","innings","innings_ball_num"]).reset_index(drop=True)
    key=["match_id","innings","innings_ball_num"]
    if x.duplicated(key).any(): raise ValueError("Duplicate delivery key match_id/innings/innings_ball_num.")
    # Match-specific innings ball limit. Revised-overs fields in this dataset
    # are stored as ball counts (e.g. 120, 114), not overs.
    lim=np.where(x.innings.eq(1),x["first_inn_revised_overs"],x["second_inn_revised_overs"])
    x["innings_ball_limit"]=pd.to_numeric(pd.Series(lim,index=x.index),errors="coerce").fillna(120).clip(lower=1)
    g=x.groupby(["match_id","innings"],sort=False)
    x["legal_balls_before"]=g["is_legal_ball"].transform(lambda s:s.astype(int).cumsum().shift(fill_value=0))
    x["score_before"]=g["team_runs"].cumsum()-x["team_runs"]
    x["wickets_before"]=g["is_wicket"].cumsum()-x["is_wicket"]
    x["wickets_before"]=x["wickets_before"].clip(0,9)
    x["wickets_remaining"]=(10-x["wickets_before"]).clip(1,10)
    x["balls_remaining"]=(x["innings_ball_limit"]-x["legal_balls_before"]).clip(lower=0)
    x["phase_fraction"]=(x["legal_balls_before"]/x["innings_ball_limit"]).clip(0,1)
    x["over_phase"]=pd.cut(x["phase_fraction"],[-.001,.333,.833,1.001],labels=["powerplay","middle","death"]).astype(str)
    x["innings_total"]=g["team_runs"].transform("sum")
    x["target"]=np.where(x.innings.eq(2),
        np.where(pd.to_numeric(x.revised_target,errors="coerce").fillna(0)>0,
                 pd.to_numeric(x.revised_target,errors="coerce"), 
                 x.groupby("match_id")["innings_total"].transform(lambda s:s.where(x.loc[s.index,"innings"].eq(1)).max()+1)),
        np.nan)
    x["runs_required"]=(x["target"]-x["score_before"]).clip(lower=0)
    x["required_run_rate"]=np.where(x.innings.eq(2),x.runs_required*6/x.balls_remaining.replace(0,np.nan),np.nan)
    x["current_run_rate"]=x["score_before"]*6/x["legal_balls_before"].replace(0,np.nan)
    # A clean, stable match result label. Tie/no-result/abandoned games are excluded from WP training.
    x["batting_team_won"]=np.where(x["win_team_id"].notna(),
        (x["batting_team_id"]==x["win_team_id"]).astype(float),np.nan)
    x.loc[x["result"].astype(str).str.contains("No Result|Abandoned|Tie",case=False,na=False),"batting_team_won"]=np.nan
    # Lagged collapse indicator: wickets lost in the previous 12 legal balls.
    x["wickets_last_12"]=0
    # Efficient per-innings lagged wicket count over the preceding 12 legal-ball
    # window. Prefix sums avoid a quadratic scan over all deliveries.
    for _,idx in x.groupby(["match_id","innings"],sort=False).groups.items():
        sub=x.loc[idx]
        legal=sub["is_legal_ball"].astype(int).to_numpy()
        wk=sub["is_wicket"].astype(int).to_numpy()
        pre_legal=np.cumsum(legal)-legal
        prefix=np.concatenate(([0],np.cumsum(wk)))
        row=np.arange(len(sub))
        left=np.searchsorted(pre_legal, np.maximum(0,pre_legal-12), side="left")
        vals=prefix[row]-prefix[left]
        x.loc[idx,"wickets_last_12"]=vals
    # The first-innings par benchmark is learned fold-by-fold in Phase 2/3
    # using only earlier matches. Phase 1 deliberately does not calculate it.
    x["par_score_expected"]=np.nan
    x["par_score_deficit"]=np.nan
    # Responsibility and situational features are observable pre-delivery proxies.
    x["collapse_stress"]=(x["wickets_last_12"]/3).clip(0,1)
    x["recovery_requirement"]=np.where(x.innings.eq(2),
        (x["required_run_rate"].fillna(0)/18).clip(0,1),
        (x["par_score_deficit"]/18).clip(0,1))
    x["partnership_dependency"]=(x["wickets_before"]/9).clip(0,1)
    x["critical_over_flag"]=x["over_phase"].eq("death").astype(int)
    out=PROC/"phase1_deliveries.csv.gz"; x.to_csv(out,index=False,compression="gzip")
    audit={"rows":len(x),"matches":int(x.match_id.nunique()),"seasons":sorted(map(int,x.season.unique())),
           "formats":x.match_format.value_counts().to_dict(),"duplicate_delivery_keys":int(x.duplicated(key).sum()),
           "super_over_rows_excluded":int(len(b)-len(x)),
           "legal_deliveries":int(x.is_legal_ball.sum()),"wide_rows":int(x.is_wide.sum()),
           "noball_rows":int(x.is_noball.sum()),"winner_label_coverage":float(x.batting_team_won.notna().mean()),
           "notes":["Overstep treated as no-ball; verify official data dictionary.",
                    "Batter balls faced excludes wides and includes no-balls.",
                    "First-innings par score is estimated fold-by-fold from earlier-match delivery states in Phase 2/3."]}
    (OUT/"phase1_audit.json").write_text(json.dumps(audit,indent=2))
    print("Phase 1 complete",audit)
    return out

FEATURES=["innings","score_before","wickets_before","wickets_remaining","legal_balls_before",
          "balls_remaining","innings_ball_limit","runs_required","required_run_rate",
          "current_run_rate","phase_fraction","match_format_code"]
def feature_frame(d):
    z=d.copy()
    z["match_format_code"]=z["match_format"].map({"T20I":1,"T20":0}).fillna(-1)
    for f in FEATURES:
        if f not in z: z[f]=0
    return z[FEATURES].replace([np.inf,-np.inf],np.nan).fillna(0)

def chronological_splits(d):
    dates=sorted(pd.to_datetime(d.match_date).dropna().dt.date.unique())
    years=sorted(d.season.unique())
    for year in years:
        tr=d[d.season<year]
        te=d[d.season==year]
        if year==years[0]:
            # Within first available season, reserve earliest 25% of distinct dates as warm-up.
            ds=sorted(pd.to_datetime(te.match_date).dt.date.unique())
            cut=max(1,int(len(ds)*.25))
            warm=set(ds[:cut]); tr=te[te.match_date.dt.date.isin(warm)]
            te=te[~te.match_date.dt.date.isin(warm)]
        if tr.match_id.nunique()>=20 and len(te):
            yield int(year),tr,te

def par_feature_frame(d):
    z=d.copy()
    z["match_format_code"]=z["match_format"].map({"T20I":1,"T20":0}).fillna(-1)
    cols=["legal_balls_before","wickets_before","innings_ball_limit","phase_fraction","match_format_code"]
    return z[cols].replace([np.inf,-np.inf],np.nan).fillna(0)

def outcome_class(d):
    # Joint next-delivery outcome: team runs (0..6, 7+) x wicket x legal-ball flag.
    runs=pd.to_numeric(d.team_runs,errors="coerce").fillna(0).clip(lower=0).astype(int).clip(upper=7)
    wk=pd.to_numeric(d.is_wicket,errors="coerce").fillna(0).astype(int).clip(0,1)
    legal=d.is_legal_ball.astype(int)
    return (runs*4 + wk*2 + legal).astype(int)

def fit_outcome_distribution(train):
    # Empirical conditional distribution with global Dirichlet smoothing.
    # Conditioning variables are known before the delivery.
    t=train.copy()
    t["wicket_band"]=pd.cut(t.wickets_before,[-1,2,5,10],labels=[0,1,2]).astype(int)
    t["rrr_band"]=pd.cut(t.required_run_rate.replace([np.inf,-np.inf],np.nan).fillna(0),[-np.inf,6,10,14,np.inf],labels=[0,1,2,3]).astype(int)
    keys=["match_format","innings","over_phase","wicket_band","rrr_band"]
    t["outcome_class"]=outcome_class(t)
    global_counts=t.outcome_class.value_counts().reindex(range(32),fill_value=0).to_numpy(dtype=float)
    global_prob=(global_counts+0.5)/(global_counts.sum()+16.0)
    grouped=t.groupby(keys+['outcome_class'],observed=False).size().unstack(fill_value=0)
    grouped=grouped.reindex(columns=range(32),fill_value=0)
    totals=grouped.sum(axis=1).to_numpy(dtype=float)
    counts=grouped.to_numpy(dtype=float)
    # 40 pseudo-deliveries from global distribution stabilize sparse states.
    probs=(counts+40.0*global_prob)/(totals[:,None]+40.0)
    lookup=grouped.copy()
    lookup.columns=[f"p_{i}" for i in range(32)]
    lookup=lookup.reset_index()
    for i in range(32): lookup[f"p_{i}"]=probs[:,i]
    return keys,lookup,global_prob

def outcome_probabilities(states, keys, lookup, global_prob):
    q=states.copy()
    q["wicket_band"]=pd.cut(q.wickets_before,[-1,2,5,10],labels=[0,1,2]).astype(int)
    q["rrr_band"]=pd.cut(q.required_run_rate.replace([np.inf,-np.inf],np.nan).fillna(0),[-np.inf,6,10,14,np.inf],labels=[0,1,2,3]).astype(int)
    merged=q[keys].merge(lookup,on=keys,how="left",sort=False)
    cols=[f"p_{i}" for i in range(32)]
    arr=merged[cols].to_numpy(dtype=float)
    bad=~np.isfinite(arr).all(axis=1)
    if bad.any(): arr[bad]=global_prob
    arr=np.nan_to_num(arr,nan=0.0)
    arr=arr/np.maximum(arr.sum(axis=1,keepdims=True),1e-12)
    return arr

def wp_features_for_state(d):
    # WP model deliberately excludes par-deficit feature. It uses only state
    # variables that can be updated consistently for hypothetical outcomes.
    z=d.copy()
    z["match_format_code"]=z["match_format"].map({"T20I":1,"T20":0}).fillna(-1)
    cols=["innings","score_before","wickets_before","wickets_remaining","legal_balls_before",
          "balls_remaining","innings_ball_limit","runs_required","required_run_rate",
          "current_run_rate","phase_fraction","match_format_code"]
    for c in cols:
        if c not in z: z[c]=0
    return z[cols].replace([np.inf,-np.inf],np.nan).fillna(0)

def expected_wpl(states, wp_model, keys, lookup, global_prob, scale_q95=None):
    """Expected absolute WP movement across all joint run/wicket/legal outcomes."""
    states=states.reset_index(drop=True).copy()
    probs=outcome_probabilities(states,keys,lookup,global_prob)
    wp_before=wp_model.predict_proba(wp_features_for_state(states))[:,1]
    wpl=np.zeros(len(states),dtype=float)
    # Process each possible outcome class. Only score states with non-negligible
    # probability for that outcome to keep memory and runtime bounded.
    for cls in range(32):
        pr=probs[:,cls]
        ix=np.flatnonzero(pr>1e-5)
        if not len(ix): continue
        run_bin=cls//4; wicket=(cls%4)//2; legal=cls%2
        z=states.iloc[ix].copy()
        z["score_before"]=(z.score_before.to_numpy()+run_bin)
        z["wickets_before"]=(z.wickets_before.to_numpy()+wicket).clip(0,10)
        z["wickets_remaining"]=(10-z.wickets_before).clip(0,10)
        z["legal_balls_before"]=(z.legal_balls_before.to_numpy()+legal)
        z["balls_remaining"]=(z.innings_ball_limit-z.legal_balls_before).clip(lower=0)
        z["phase_fraction"]=(z.legal_balls_before/z.innings_ball_limit).clip(0,1)
        z["current_run_rate"]=z.score_before*6/z.legal_balls_before.replace(0,np.nan)
        chase=z.innings.eq(2)
        z["runs_required"]=(z.target-z.score_before).clip(lower=0)
        z["required_run_rate"]=np.where(chase,z.runs_required*6/z.balls_remaining.replace(0,np.nan),np.nan)
        # Terminal chase states are exact, not model extrapolations.
        wp_after=wp_model.predict_proba(wp_features_for_state(z))[:,1]
        completed=(z.innings.eq(2)&(z.runs_required<=0))
        all_out=(z.wickets_remaining<=0)&z.innings.eq(2)
        exhausted=(z.balls_remaining<=0)&z.innings.eq(2)
        wp_after=np.where(completed,1.0,wp_after)
        wp_after=np.where(all_out&~completed,0.0,wp_after)
        # For a chase that has exhausted its balls, the batting side has failed.
        wp_after=np.where(exhausted&(z.runs_required>0),0.0,wp_after)
        wpl[ix]+=pr[ix]*np.abs(wp_after-wp_before[ix])
    if scale_q95 is not None and scale_q95>0:
        return np.clip(wpl/scale_q95,0,1),wpl
    return wpl,wpl

def fit_par_model(train):
    # Predict the par score at the current legal-ball/wicket state, using only
    # prior-match first-innings states. A temporal calibration slice estimates
    # a fold-specific intercept correction before the final all-training refit.
    z=train[(train.innings==1)&train.batting_team_won.notna()].copy()
    if len(z)<500: return None,0.0
    dates=sorted(pd.to_datetime(z.match_date).dt.date.unique())
    offset=0.0
    if len(dates)>=10:
        cut=max(1,int(len(dates)*.85))
        fit_dates=set(dates[:cut]); cal_dates=set(dates[cut:])
        fit=z[z.match_date.dt.date.isin(fit_dates)]
        cal=z[z.match_date.dt.date.isin(cal_dates)]
        if len(fit)>=300 and len(cal)>=100:
            cal_model=HistGradientBoostingRegressor(max_iter=160,learning_rate=.05,max_leaf_nodes=20,
                min_samples_leaf=80,l2_regularization=3,random_state=SEED)
            cal_model.fit(par_feature_frame(fit),fit.score_before.clip(lower=0))
            offset=float(np.mean(cal.score_before.to_numpy()-cal_model.predict(par_feature_frame(cal))))
    model=HistGradientBoostingRegressor(max_iter=160,learning_rate=.05,max_leaf_nodes=20,
        min_samples_leaf=80,l2_regularization=3,random_state=SEED)
    model.fit(par_feature_frame(z),z.score_before.clip(lower=0))
    return model,offset

def phase2_3():
    d=pd.read_csv(PROC/"phase1_deliveries.csv.gz",low_memory=False)
    d["match_date"]=pd.to_datetime(d.match_date)
    preds=[]; wp_metrics=[]; exp_metrics=[]; par_metrics=[]; wpl_metrics=[]
    for year,tr,te in chronological_splits(d):
        if set(tr.match_id)&set(te.match_id): raise AssertionError("Match overlap in chronological split")
        # Train the par curve only on earlier matches, then apply to scored season.
        par_model,par_offset=fit_par_model(tr)
        te=te.copy()
        if par_model is not None:
            first_mask=te.innings.eq(1)
            te["par_score_expected"]=np.nan
            te.loc[first_mask,"par_score_expected"]=np.maximum(par_model.predict(par_feature_frame(te.loc[first_mask]))+par_offset,0)
            te["par_score_deficit"]=(te.par_score_expected-te.score_before).where(first_mask,0)
        else:
            te["par_score_expected"]=np.nan; te["par_score_deficit"]=np.nan
        # Par model evaluation: score prediction against observed score at state.
        pm=te[te.innings.eq(1)&te.par_score_expected.notna()]
        if len(pm):
            par_metrics.append({"year":year,"rows":len(pm),"calibration_offset":float(par_offset),
                "par_score_mae":float(mean_absolute_error(pm.score_before,pm.par_score_expected)),
                "par_score_bias_pred_minus_actual":float((pm.par_score_expected-pm.score_before).mean())})
        Xtr=wp_features_for_state(tr); Xte=wp_features_for_state(te)
        wtr=tr.batting_team_won.notna()
        if tr.loc[wtr,"batting_team_won"].nunique()==2:
            # No class balancing: preserve probability calibration.
            wp=make_pipeline(StandardScaler(),LogisticRegression(max_iter=600,C=.35))
            wp.fit(Xtr.loc[wtr],tr.loc[wtr,"batting_team_won"].astype(int))
        else:
            raise RuntimeError(f"Insufficient both-class winner labels in training fold {year}")
        wp_pre=wp.predict_proba(Xte)[:,1]
        # Delivery outcome distribution learned exclusively from the training fold.
        keys,lookup,global_prob=fit_outcome_distribution(tr)
        # WPL normalization: q95 from a deterministic sample of training states.
        # This is a scale calibration only; no scored-season outcomes are used.
        cal=tr.sample(n=min(12000,len(tr)),random_state=SEED).copy()
        raw_cal,_=expected_wpl(cal,wp,keys,lookup,global_prob,None)
        q95=float(np.quantile(raw_cal,.95)) if len(raw_cal) else .10
        q95=max(q95,.005)
        wpl_norm,wpl_raw=expected_wpl(te,wp,keys,lookup,global_prob,q95)
        # Expected performance models
        br=HistGradientBoostingRegressor(max_iter=120,learning_rate=.06,max_leaf_nodes=15,l2_regularization=2,random_state=SEED)
        bw=HistGradientBoostingRegressor(max_iter=120,learning_rate=.06,max_leaf_nodes=15,l2_regularization=2,random_state=SEED+1)
        wk=HistGradientBoostingClassifier(max_iter=100,learning_rate=.06,max_leaf_nodes=15,l2_regularization=2,random_state=SEED+2)
        exp_Xtr=feature_frame(tr); exp_Xte=feature_frame(te)
        br.fit(exp_Xtr,tr.runs.clip(0,6)); bw.fit(exp_Xtr,tr.bowler_runs_conceded.clip(0,10)); wk.fit(exp_Xtr,tr.bowler_wicket.astype(int))
        out=te[["match_id","innings","innings_ball_num","match_date","season","match_format",
                "striker_id","striker_name","bowler_id","bowler_name","batting_team_id","bowling_team_id",
                "is_legal_ball","batter_ball_faced","runs","bowler_runs_conceded","bowler_wicket",
                "batting_team_won","score_before","wickets_before","legal_balls_before","balls_remaining",
                "innings_ball_limit","target","runs_required","required_run_rate","current_run_rate",
                "phase_fraction","par_score_expected","par_score_deficit"]].copy()
        out["expected_batter_runs"]=br.predict(exp_Xte).clip(0,6)
        out["expected_bowler_runs_conceded"]=bw.predict(exp_Xte).clip(0,10)
        out["expected_bowler_wicket_prob"]=wk.predict_proba(exp_Xte)[:,1]
        out["wp_pre"]=wp_pre
        out["wpl_raw"]=wpl_raw
        out["wpl_score"]=wpl_norm
        out["wpl_reference_q95"]=q95
        out["prediction_year"]=year
        preds.append(out)
        exp_metrics.append({"year":year,"rows":len(te),
            "batter_runs_mae":float(mean_absolute_error(te.runs,out.expected_batter_runs)),
            "bowler_runs_mae":float(mean_absolute_error(te.bowler_runs_conceded,out.expected_bowler_runs_conceded))})
        valid=te.batting_team_won.notna()
        if valid.sum() and len(np.unique(te.loc[valid,"batting_team_won"]))==2:
            y_valid=te.loc[valid,"batting_team_won"].astype(int).to_numpy()
            p_valid=wp_pre[valid.to_numpy()]
            cal_df=pd.DataFrame({"p":p_valid,"y":y_valid})
            cal_df["bin"]=pd.qcut(cal_df.p,10,duplicates="drop")
            rel=cal_df.groupby("bin",observed=True).agg(predicted=("p","mean"),observed=("y","mean"),n=("y","size"))
            ece=float((rel.n/rel.n.sum()*(rel.predicted-rel.observed).abs()).sum())
            wp_metrics.append({"year":year,"rows":int(valid.sum()),
                "brier":float(brier_score_loss(y_valid,p_valid)),
                "log_loss":float(log_loss(y_valid,np.clip(p_valid,1e-6,1-1e-6))),
                "roc_auc":float(roc_auc_score(y_valid,p_valid)),"expected_calibration_error":ece})
        wpl_metrics.append({"year":year,"wpl_raw_mean":float(np.mean(wpl_raw)),"wpl_raw_q95":float(q95),
                            "wpl_scaled_mean":float(np.mean(wpl_norm)),"wpl_scaled_q95":float(np.quantile(wpl_norm,.95))})
    if not preds: raise RuntimeError("No chronological model folds were trainable. Check dates and match coverage.")
    p=pd.concat(preds,ignore_index=True)
    p.to_csv(PROC/"oos_predictions.csv.gz",index=False,compression="gzip")
    (OUT/"model_metrics.json").write_text(json.dumps({"expected_performance":exp_metrics,"win_probability":wp_metrics,
        "first_innings_par_model":par_metrics,"win_probability_leverage":wpl_metrics},indent=2))
    print("Phase 2/3 complete: OOS predictions",len(p),"with expected-outcome WPL and rolling first-innings par model")
    return p

def phase4_pressure():
    d=pd.read_csv(PROC/"phase1_deliveries.csv.gz",low_memory=False)
    d["match_date"]=pd.to_datetime(d.match_date)
    pred=pd.read_csv(PROC/"oos_predictions.csv.gz",low_memory=False)
    keys=["match_id","innings","innings_ball_num"]
    pred_cols=keys+["wp_pre","wpl_raw","wpl_score","par_score_expected","par_score_deficit"]
    d=d.drop(columns=[c for c in ["wp_pre","wpl_raw","wpl_score","par_score_expected","par_score_deficit"] if c in d.columns])
    d=d.merge(pred[pred_cols],on=keys,how="left",validate="one_to_one")
    d["par_score_deficit"]=pd.to_numeric(d.par_score_deficit,errors="coerce").fillna(0)
    # Match-state difficulty: chase difficulty vs current scoring pace; first innings
    # uses modelled historical par deficit at the exact pre-delivery state.
    chase=d.innings.eq(2)
    rrr_stress=((d.required_run_rate.fillna(0)-d.current_run_rate.fillna(0)).clip(lower=0)/8).clip(0,1)
    wicket_stress=((10-d.wickets_remaining)/10).clip(0,1)**1.5
    first_par=(d.par_score_deficit.clip(lower=0)/18).clip(0,1)
    d["msd"]=np.where(chase,.60*rrr_stress+.40*wicket_stress,.65*first_par+.35*wicket_stress)
    ball_fraction=(d.balls_remaining/d.innings_ball_limit).clip(0,1)
    d["rsi"]=1-(ball_fraction*(d.wickets_remaining/10).clip(0,1))
    d["recovery_requirement"]=np.where(chase,(d.required_run_rate.fillna(0)/18).clip(0,1),
                                           (d.par_score_deficit.clip(lower=0)/18).clip(0,1))
    d["ssi"]=.35*d.collapse_stress+.30*d.recovery_requirement+.20*d.partnership_dependency+.15*d.critical_over_flag
    d["pep"]=d.phase_fraction*np.maximum(d.msd,.5*d.rsi)
    # Full expected-outcome WPL from fold-specific models; scaled by prior-fold q95.
    d["wpl"]=pd.to_numeric(d.wpl_score,errors="coerce").fillna(0).clip(0,1)
    d["hdpi_score"]=100*(.25*d.msd+.30*d.wpl+.20*d.rsi+.15*d.ssi+.10*d.pep)
    d["hdpi_band"]=pd.cut(d.hdpi_score,[-.001,40,60,75,90,100.001],
        labels=["Routine","Elevated","High","Severe","Critical"]).astype(str)
    d["is_pressure"]=d.hdpi_score.ge(60)
    d["batter_urgency"]=np.where(chase,(d.required_run_rate.fillna(0)/18).clip(0,1),
                                   (d.phase_fraction*.55+d.par_score_deficit.clip(lower=0).div(30).clip(0,1)*.45))
    d["dismissal_risk"]=(d.wickets_remaining.le(3).astype(float)*.6+d.partnership_dependency*.4).clip(0,1)
    d["batter_responsibility"]=(.6*d.partnership_dependency+.4*d.wickets_last_12.div(3).clip(0,1)).clip(0,1)
    d["bowler_defence_urgency"]=np.where(chase,(d.required_run_rate.fillna(0)/18).clip(0,1),
                                           (d.phase_fraction*.6+d.par_score_deficit.clip(lower=0).div(30).clip(0,1)*.4))
    d["wicket_threat"]=(d.wickets_before.div(8).clip(0,1)*.5+d.wickets_last_12.div(3).clip(0,1)*.5)
    d["bowler_responsibility"]=(.6*d.bowler_defence_urgency+.4*d.critical_over_flag).clip(0,1)
    d["bpi_score"]=100*(.35*d.hdpi_score/100+.25*d.batter_urgency+.20*d.dismissal_risk+.20*d.batter_responsibility)
    d["bopi_score"]=100*(.35*d.hdpi_score/100+.25*d.bowler_defence_urgency+.20*d.wicket_threat+.20*d.bowler_responsibility)
    d["bpi_pressure"]=d.bpi_score.ge(60); d["bopi_pressure"]=d.bopi_score.ge(60)
    d.to_csv(PROC/"deliveries_v2_pressure.csv.gz",index=False,compression="gzip")
    print("Phase 4 complete: fold-specific expected-outcome WPL and chronological first-innings par scores applied.")
    return d

def eb_shrink(raw, se2, prior_mask=None):
    # Normal-normal empirical Bayes. Estimate between-player variance only from
    # the relaxed-eligible pool; otherwise players with no pressure/normal sample
    # would inflate the sampling-variance estimate and collapse every posterior.
    raw=np.asarray(raw,float); se2=np.asarray(se2,float)
    valid=np.isfinite(raw)&np.isfinite(se2)
    if prior_mask is not None:
        valid &= np.asarray(prior_mask,dtype=bool)
    if valid.sum()<3: return raw.copy()
    tau2=max(float(np.nanvar(raw[valid],ddof=1)-np.nanmean(se2[valid])),1e-8)
    return raw*tau2/(tau2+np.maximum(se2,1e-8))

def phase5_rank():
    d=pd.read_csv(PROC/"deliveries_v2_pressure.csv.gz",low_memory=False)
    p=pd.read_csv(PROC/"oos_predictions.csv.gz",low_memory=False)
    keys=["match_id","innings","innings_ball_num"]
    p=p[keys+["expected_batter_runs","expected_bowler_runs_conceded","expected_bowler_wicket_prob"]]
    d=d.merge(p,on=keys,how="inner",validate="one_to_one")
    d["batter_residual"]=d.runs-d.expected_batter_runs
    d["bowler_residual"]=d.expected_bowler_runs_conceded-d.bowler_runs_conceded
    # Intensity weighting is applied to residuals; the unweighted residual is retained.
    d["batter_weighted_resid"]=d.batter_residual*(d.bpi_score/100).clip(0,1)**1.5
    d["bowler_weighted_resid"]=d.bowler_residual*(d.bopi_score/100).clip(0,1)**1.5
    d["batter_exposure"]=d.batter_ball_faced.astype(int)
    d["bowler_exposure"]=d.is_legal_ball.astype(int)
    results={}
    for role in ["batter","bowler"]:
        pid="striker_id" if role=="batter" else "bowler_id"
        name="striker_name" if role=="batter" else "bowler_name"
        flag="bpi_pressure" if role=="batter" else "bopi_pressure"
        resid=f"{role}_weighted_resid"; exposure=f"{role}_exposure"
        m=d.groupby([pid,name,"match_id","season","match_format",flag],dropna=False).agg(
            residual=(resid,"sum"),exposure=(exposure,"sum")).reset_index()
        rows=[]
        for player,g in m.groupby(pid,dropna=True):
            nm=g[name].dropna().iloc[0] if g[name].notna().any() else str(player)
            a=g[g[flag]]; b=g[~g[flag]]
            pe=a.exposure.sum(); ne=b.exposure.sum()
            pr=100*a.residual.sum()/pe if pe else np.nan
            nr=100*b.residual.sum()/ne if ne else np.nan
            lift=pr-nr if np.isfinite(pr) and np.isfinite(nr) else np.nan
            # Conservative match-cluster variance proxy; final intervals use bootstrap below.
            se2=(100**2)*(np.nanvar(a.residual,ddof=1)/max(pe,1)**2 if len(a)>1 else 1)+(
                np.nanvar(b.residual,ddof=1)/max(ne,1)**2 if len(b)>1 else 1)
            rows.append({"player_id":player,"player_name":nm,"pressure_matches":a.match_id.nunique(),
                "normal_matches":b.match_id.nunique(),"pressure_balls":pe,"normal_balls":ne,
                "pressure_rate":pr,"normal_rate":nr,"raw_lift":lift,"se2_proxy":se2})
        s=pd.DataFrame(rows)
        relaxed=THRESHOLDS["relaxed"]
        prior_mask=((s.pressure_matches>=relaxed["pressure_matches"]) &
                    (s.normal_matches>=relaxed["normal_matches"]) &
                    (s.pressure_balls>=relaxed["pressure_balls"]) &
                    (s.normal_balls>=relaxed["normal_balls"]))
        s["eb_lift"]=eb_shrink(s.raw_lift,s.se2_proxy,prior_mask)
        # Match-cluster bootstrap: resample player-match clusters separately by pressure state.
        rng=np.random.default_rng(SEED)
        boot_prob=[]; lo=[]; hi=[]
        # Bootstrap only players who meet the relaxed exposure floor; 120
        # cluster resamples are sufficient for a screening interval. Increase
        # to 1,000 for the final locked submission run.
        relaxed=THRESHOLDS["relaxed"]
        for _,r in s.iterrows():
            eligible_boot=(r.pressure_matches>=relaxed["pressure_matches"] and
                           r.normal_matches>=relaxed["normal_matches"] and
                           r.pressure_balls>=relaxed["pressure_balls"] and
                           r.normal_balls>=relaxed["normal_balls"])
            if not eligible_boot:
                boot_prob.append(np.nan); lo.append(np.nan); hi.append(np.nan); continue
            g=m[m[pid]==r.player_id]
            draws=[]
            for _ in range(40):
                rates=[]
                for state in [True,False]:
                    z=g[g[flag]==state]
                    if z.empty or z.exposure.sum()==0: rates.append(np.nan); continue
                    ix=rng.integers(0,len(z),len(z))
                    zz=z.iloc[ix]
                    rates.append(100*zz.residual.sum()/max(zz.exposure.sum(),1))
                if np.isfinite(rates).all(): draws.append(rates[0]-rates[1])
            if draws:
                arr=np.asarray(draws); boot_prob.append(float((arr>0).mean()))
                lo.append(float(np.quantile(arr,.025))); hi.append(float(np.quantile(arr,.975)))
            else: boot_prob.append(np.nan); lo.append(np.nan); hi.append(np.nan)
        s["bootstrap_prob_positive"]=boot_prob; s["bootstrap_ci_low"]=lo; s["bootstrap_ci_high"]=hi
        for label,t in THRESHOLDS.items():
            s[f"eligible_{label}"]=((s.pressure_matches>=t["pressure_matches"])&
                (s.normal_matches>=t["normal_matches"])&
                (s.pressure_balls>=t["pressure_balls"])&
                (s.normal_balls>=t["normal_balls"]))
            eligible=s[s[f"eligible_{label}"]].copy()
            eligible=eligible.sort_values(["eb_lift","bootstrap_prob_positive","bootstrap_ci_low",
                                            "raw_lift","pressure_matches"],ascending=[False,False,False,False,False])
            eligible.insert(0,"rank",range(1,len(eligible)+1))
            eligible.head(10).to_csv(OUT/f"top10_{role}s_{label}.csv",index=False)
        s.to_csv(OUT/f"{role}_all_player_scores.csv",index=False)
        results[role]=s
    # Threshold sensitivity summary.
    sens=[]
    for role in ["batters","bowlers"]:
        ids={}
        for level in THRESHOLDS:
            f=OUT/f"top10_{role}_{level}.csv"
            z=pd.read_csv(f) if f.exists() else pd.DataFrame()
            ids[level]=set(z.player_id) if len(z) else set()
        for level in THRESHOLDS:
            sens.append({"role":role,"threshold":level,"top10_count":len(ids[level]),
                "overlap_with_current":len(ids[level]&ids["current"])})
    pd.DataFrame(sens).to_csv(OUT/"threshold_sensitivity.csv",index=False)
    print("Phase 5 complete: ranking outputs generated.")
    return results

def phase6_report():
    report={
      "project":"CLUTCH IQ 2.0",
      "status":"Upgraded research implementation: WPL is expected absolute win-probability movement over a past-only joint delivery-outcome distribution; first-innings par is a fold-specific historical state model. Requires calibration and subgroup validation before final competition claims.",
      "thresholds":THRESHOLDS,
      "weights":HDPI_W,
      "wpl_definition":"WPL(S) = sum_o P(o|S) * abs(WP(S_o)-WP(S)). Outcome o jointly represents team runs (0..6 or 7+), wicket indicator, and legal-ball indicator. Conditional probabilities use only prior-fold deliveries and Dirichlet smoothing toward the fold-wide outcome distribution.",
      "par_definition":"A fold-specific HistGradientBoostingRegressor predicts the expected score_before at each first-innings state from match format, legal balls elapsed, wickets lost, innings length and phase. It is trained only on earlier matches. Par deficit = predicted par score - actual pre-delivery score.",
      "required_review":[
        "Inspect WPL outcome support and WP calibration by format, innings and phase.",
        "Inspect first-innings par MAE and prediction bias by phase and wickets-lost band.",
        "Run pressure-weight ablation and weight sensitivity.",
        "Reserve 2026 as a final untouched holdout during model/weight selection.",
        "Audit no-ball/Overstep and batter balls-faced scoring convention against official data dictionary.",
        "Report format-specific T20/T20I robustness and minimum eligible-player coverage."
      ]
    }
    (OUT/"methodology_and_validation_report.json").write_text(json.dumps(report,indent=2))
    print("Phase 6 report complete.")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase",choices=["1","2-3","4","5","6","all"],default="all")
    args=ap.parse_args()
    if args.phase in ["1","all"]: phase1()
    if args.phase in ["2-3","all"]: phase2_3()
    if args.phase in ["4","all"]: phase4_pressure()
    if args.phase in ["5","all"]: phase5_rank()
    if args.phase in ["6","all"]: phase6_report()

if __name__=="__main__": main()
