import openvsp as vsp
import pandas as pd
from pathlib import Path
import yaml
from importlib.resources import files
import jsonschema


def restart(fname: str | Path) -> None:
    vsp.VSPRenew()
    vsp.ReadVSPFile(str(fname))


def parse_parm_change(cstring: str):
    c, g, p, v = cstring.split(":")
    v = float(v)
    return c, g, p, v


def change_parm(container: str, group: str, parm: str, value: float) -> None:
    gid = vsp.FindContainer(container, 0)
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


def res2lst(rid: str, col: str) -> tuple[float | str | int]:
    get_funs = {
        vsp.INT_DATA: vsp.GetIntResults,
        vsp.DOUBLE_DATA: vsp.GetDoubleResults,
        vsp.STRING_DATA: vsp.GetStringResults
    }
    fun = get_funs[vsp.GetResultsType(rid, col)]
    v = fun(rid, col)
    return v


def res2df(rid: str, cols: list[str]) -> pd.DataFrame:
    df = pd.DataFrame()
    for c in cols:
        df[c] = res2lst(rid, c)
    return df


def get_load_results() -> pd.DataFrame:
    def load_df(idx):
        rid = vsp.FindResultsID("VSPAERO_Load", idx)
        aoa = vsp.GetDoubleResults(rid, "FC_AoA_")[0]
        df = res2df(rid,
                    ["WingId", "Yavg", "cl*c/cref", "cd*c/cref",
                     "cmy*c/cref", "Chord"])
        df['aoa'] = aoa
        df['aoa_idx'] = idx
        return df
    dflst = [load_df(i) for i in range(vsp.GetNumResults("VSPAERO_Load"))]
    df = pd.concat(dflst, ignore_index=True, sort=False)
    return df


def get_vspaero_refs() -> tuple[float]:
    rid = vsp.FindLatestResultsID("VSPAERO_Load")
    b_ref = res2lst(rid, "FC_Bref_")[0]
    c_ref = res2lst(rid, "FC_Cref_")[0]
    S_ref = res2lst(rid, "FC_Sref_")[0]
    x_ref = res2lst(rid, "FC_Xcg_")[0]
    y_ref = res2lst(rid, "FC_Ycg_")[0]
    z_ref = res2lst(rid, "FC_Zcg_")[0]

    return b_ref, c_ref, S_ref, x_ref, y_ref, z_ref


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


def get_parasite_sref() -> float:
    rid = vsp.FindLatestResultsID("Parasite_Drag")
    sref = vsp.GetDoubleResults(rid, "FC_Sref")
    return sref[0]


class VspuException(Exception):
    pass


class Refs:
    def __init__(self, b=1, c=1, S=1, x=1, y=1, z=1):
        self.b = b
        self.c = c
        self.S = S
        self.x = x
        self.y = y
        self.z = z
        self.S_CD0 = None


class Runner:

    def __init__(self, case_dict: dict):
        self.d = case_dict
        self.name = case_dict['name']
        self.polar = None
        self.load = None
        self.geom_drag = None
        self.excres_drag = None
        self.sweep = None
        self.refs = Refs()

        self.errorMgr = vsp.ErrorMgrSingleton.getInstance()
        self.errorMgr.SilenceErrors()

    def rerr(self):
        '''Check and raise errors'''
        errs = [self.errorMgr.PopLastError().GetErrorString()
                for i in range(self.errorMgr.GetNumTotalErrors())][::-1]
        if errs:
            raise VspuException('\n'.join(errs))

    def restart(self):
        restart(self.d['fname'])
        self.rerr()

    def change_model(self):
        changes = self.d.get('changes')
        for change in changes or []:
            c, g, p, v = parse_parm_change(change)
            change_parm(c, g, p, v)
        self.rerr()

    def exec_an(self):
        for an, cfg in self.d['analyses'].items():
            vsp.SetAnalysisInputDefaults(an)
            if cfg is not None:
                for name, value in cfg.items():
                    change_an_input(an, name, value)

            vsp.ExecAnalysis(an)

            if an == "VSPAEROSweep":
                self.polar = get_polar_results()
                self.load = get_load_results()
                self.refs = Refs(*get_vspaero_refs())
            if an == "ParasiteDrag":
                self.geom_drag = get_geom_drag()
                self.excres_drag = get_excres_drag()
                self.refs.S_CD0 = get_parasite_sref()

        vsp.DeleteAllResults()
        self.rerr()


def load_yaml(fname: str | Path, validate: bool = True) -> list[Runner]:
    with open(str(fname)) as fp:
        d = yaml.safe_load(fp)
    if validate:
        schema_path = files("vsputils.schemas").joinpath("cases.json")
        with schema_path.open("r") as fp:
            sc = yaml.safe_load(fp)
        jsonschema.validate(instance=d, schema=sc)

    return [Runner(case_dict) for case_dict in d['cases']]
