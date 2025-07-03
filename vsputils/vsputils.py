import openvsp as vsp
import pandas as pd
from pathlib import Path


def restart(fname: str | Path) -> None:
    vsp.VSPRenew()
    vsp.ReadVSPFile(str(fname))


def parse_parm_change(cstring: str):
    c, g, p, v = cstring.split(":")
    v = float(v)
    return c, g, p, v


def change_parm(container: str, group: str, parm: str, value: float) -> None:
    gid = vsp.FindGeom(container, 0)
    vsp.SetParmVal(gid, parm, group, value)
    vsp.Update()


def change_an_input(an: str, name: str, value: float | int | str) -> None:
    '''Note: value is a single value, without having to wrap it into a list.'''
    set_funs = {
        vsp.INT_DATA: vsp.SetIntAnalysisInput,
        vsp.DOUBLE_DATA: vsp.SetDoubleAnalysisInput,
        vsp.STRING_DATA: vsp.SetStringAnalysisInput
    }
    fun = set_funs[vsp.GetAnalysisInputType(an, name)]
    fun(an, name, [value])


def res2df(rid: str, cols: list[str]) -> pd.DataFrame:
    get_funs = {
        vsp.INT_DATA: vsp.GetIntResults,
        vsp.DOUBLE_DATA: vsp.GetDoubleResults,
        vsp.STRING_DATA: vsp.GetStringResults
    }

    df = pd.DataFrame()
    for c in cols:
        fun = get_funs[vsp.GetResultsType(rid, c)]
        v = fun(rid, c)
        df[c] = v
    return df


def get_load_results():
    def load_df(idx):
        rid = vsp.FindResultsID("VSPAERO_Load", idx)
        aoa = vsp.GetDoubleResults(rid, "FC_AoA_")[0]
        df = res2df(rid,
                    ["WingId", "Yavg", "cl*c/cref", "cd*c/cref", "cmy*c/cref"])
        df['aoa'] = aoa
        df['aoa_idx'] = idx
        return df
    dflst = [load_df(i) for i in range(vsp.GetNumResults("VSPAERO_Load"))]
    df = pd.concat(dflst, ignore_index=True, sort=False)
    return df


def get_polar_results() -> pd.DataFrame:
    rid = vsp.FindLatestResultsID("VSPAERO_Polar")
    df = res2df(rid, ["Alpha", "CDi", "CDo", "CDt", "CMy", "CL"])
    return df


def get_geom_drag() -> pd.DataFrame:
    rid = vsp.FindLatestResultsID("Parasite_Drag")
    df = res2df(rid, ["Comp_CD", "Comp_f", "Comp_Swet"])
    return df


def get_excres_drag() -> pd.DataFrame:
    rid = vsp.FindLatestResultsID("Parasite_Drag")
    df = res2df(rid, ["Excres_Amount", "Excres_f"])
    return df


def run_case(fname: str, case_dict: dict):

    _results_map = {
        "VSPAEROSweep": [get_load_results, get_polar_results],
        "ParasiteDrag": [get_geom_drag, get_excres_drag]
    }

    res = []

    restart(fname)
    changes = case_dict.get('changes', None)
    for change in changes or []:
        c, g, p, v = parse_parm_change(change)
        change_parm(c, g, p, v)

    for an, cfg in case_dict['analyses'].items():
        vsp.SetAnalysisInputDefaults(an)
        if cfg is not None:
            for name, value in cfg.items():
                change_an_input(an, name, value)

        vsp.ExecAnalysis(an)

        for f in _results_map.get(an) or []:
            res.append(f)

    vsp.DeleteAllResults()

    return res
