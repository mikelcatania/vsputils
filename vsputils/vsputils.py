import openvsp as vsp
import pandas as pd
from pathlib import Path
import yaml
from importlib.resources import files
import jsonschema
from spq.spq.aero import Dens, Vel


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


def parse_airfoil_change(cstring: str):
    container, sec_num, fname = cstring.split(':')
    sec_num = int(sec_num)
    return container, sec_num, fname


def change_airfoil(container: str, sec_num: int, fname: str | Path) -> None:
    gid = vsp.FindContainer(container, 0)
    sid = vsp.GetXSecSurf(gid, 0)
    vsp.ChangeXSecShape(sid, sec_num, vsp.XS_FILE_AIRFOIL)
    xsec = vsp.GetXSec(sid, sec_num)
    vsp.ReadFileAirfoil(xsec, str(fname))
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
                    ["VortexSheet", "Yavg", "cl*c/cref", "cdi*c/cref",
                     "cmyi*c/cref", "Chord"])
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
    df = res2df(rid, ["Alpha", "CDi", "CDo", "CDiw", "CMiy", "CLi"])
    return df


def get_geom_drag() -> pd.DataFrame:
    rid = vsp.FindLatestResultsID("Parasite_Drag")
    df = res2df(rid, ["Comp_CD", "Comp_f", "Comp_Swet"])
    return df


def get_excres_drag() -> pd.DataFrame:
    rid = vsp.FindLatestResultsID("Parasite_Drag")
    df = res2df(rid, ["Excres_Amount", "Excres_f"])
    return df


def get_parasite_refs() -> float:
    rid = vsp.FindLatestResultsID("Parasite_Drag")
    S_ref = vsp.GetDoubleResults(rid, "FC_Sref")[0]

    # Density.
    dens_value = vsp.GetDoubleResults(rid, "FC_Rho")[0]
    dens_unit = vsp.GetStringResults(rid, "Rho_Label")[0]
    if "slug" in dens_unit:
        ρ = Dens.fromslugft3(dens_value)
    elif "kg" in dens_unit:
        ρ = Dens.fromkgm3(dens_value)

    # Velocity.
    vel_value = vsp.GetDoubleResults(rid, "FC_Vinf")[0]
    vel_unit  = vsp.GetStringResults(rid, "Vinf_Label")[0]
    if "KEAS" in vel_unit:
        vel = Vel.fromkt(vel_value)
        ρ = Dens(1.225)
    elif "KTAS" in vel_unit:
        vel = Vel.fromkt(vel_value)
    elif "ft/s" in vel_unit:
        vel = Vel.fromfps(vel_value)
    elif "m/s" in vel_unit:
        vel = Vel.fromms(vel_value)
    elif "mph" in vel_unit:
        vel = Vel.frommph(vel_value)
    elif "km/h" in vel_unit:
        vel = Vel.fromkmh(vel_value)
        
    return ρ, vel, S_ref


def get_mass_results() -> tuple[float, list[float]]:
    rid = vsp.FindLatestResultsID('Mass_Properties')
    mass = res2lst(rid, 'Total_Mass')[0]
    cg_vec = vsp.GetVec3dResults(rid, 'Total_CG')[0]
    cg = [cg_vec.x(), cg_vec.y(), cg_vec.z()]
    return mass, cg


class VspuException(Exception):
    pass


class Refs:

    def __init__(self, **kwargs):
        self.add(**kwargs)
    
    def add(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def add_vspaero_refs(self, bcSxyz_tuple: tuple[float]):
        if len(bcSxyz_tuple) != 6:
            raise ValueError(
                "Tuple must have exactly 6 elements: (b, c, S, x, y, z)")
        for k, v in zip('bcSxyz', bcSxyz_tuple):
            self.add(**{k:v})

    def add_parasite_refs(self, ρvS_tuple: tuple[float]):
        if len(ρvS_tuple) != 3:
            raise ValueError(
                "Tuple must have exactly 3 elements: (ρ, vel, S)")
        for k, v in zip('ρvS', ρvS_tuple):
            self.add(**{k:v})
        
    def __repr__(self):
        attrs = ', '.join(f'{key}={value!r}' for key, value in self.__dict__.items())
        return f'{self.__class__.__name__}({attrs})'


def rerr(errorMgr: vsp.ErrorMgrSingleton):
    errs = [errorMgr.PopLastError().GetErrorString()
            for i in range(errorMgr.GetNumTotalErrors())][::-1]
    if errs:
        raise VspuException('\n'.join(errs))


class Runner:

    def __init__(self, case_dict: dict):
        self.d = case_dict
        self.name = case_dict['name']
        self.polar = None
        self.load = None
        self.geom_drag = None
        self.excres_drag = None
        self.aero_refs = Refs()
        self.parasite_refs = Refs()

        self.errorMgr = vsp.ErrorMgrSingleton.getInstance()
        self.errorMgr.SilenceErrors()

    def rerr(self):
        '''Check and raise errors'''
        rerr(self.errorMgr)

    def restart(self):
        restart(self.d['fname'])
        self.rerr()

    def change_model(self):
        changes = self.d.get('changes')
        for change in changes or []:
            c, g, p, v = parse_parm_change(change)
            change_parm(c, g, p, v)
        self.rerr()

    def change_airfoils(self):
        for af in self.d.get('airfoils', []):
            container, sec_num, fname = parse_airfoil_change(af)
            change_airfoil(container, sec_num, fname)
        self.rerr()

    def del_subsurf(self):
        if not self.d.get('del_subsurf'):
            return
        for sid in vsp.GetAllSubSurfIDs():
            vsp.DeleteSubSurf(sid)
        vsp.Update()

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
                self.aero_refs.add_vspaero_refs(get_vspaero_refs())
            if an == "ParasiteDrag":
                self.geom_drag = get_geom_drag()
                self.excres_drag = get_excres_drag()
                self.parasite_refs.add_parasite_refs(get_parasite_refs())

        vsp.DeleteAllResults()
        self.rerr()

    def run_all(self):
        self.restart()
        self.change_model()
        self.change_airfoils()
        self.del_subsurf()
        self.exec_an()

def load_yaml_dict(fname: str | Path, validate: bool = True) -> dict:
    with open(str(fname)) as fp:
        d = yaml.safe_load(fp)
    if validate:
        schema_path = files("vsputils.schemas").joinpath("cases.json")
        with schema_path.open("r") as fp:
            sc = yaml.safe_load(fp)
        jsonschema.validate(instance=d, schema=sc)
    return d

def load_yaml(fname: str | Path, validate: bool = True) -> list[Runner]:
    d = load_yaml_dict(fname, validate)
    return [Runner(case_dict) for case_dict in d['cases']]
