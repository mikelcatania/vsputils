import openvsp as vsp
import pandas as pd
from pathlib import Path
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
    try:
        fun = set_funs[vsp.GetAnalysisInputType(an, name)]
    except KeyError:
        raise KeyError(f'Input "{name}" not supported for analysis {an}')
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
                    ["VortexSheet", "Xavg", "Yavg", "Zavg", "cl*c/cref",
                     "cdi*c/cref",  "cmyi*c/cref", "Chord"])
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
    df = res2df(rid, ["Alpha", "CDi", "CDo", "CDiw", "CMiy", "CLiw"])
    return df


def get_geom_drag() -> pd.DataFrame:
    rid = vsp.FindLatestResultsID("Parasite_Drag")
    df = res2df(rid, ["Comp_CD", "Comp_f", "Comp_Swet"])
    return df


def get_excres_drag() -> pd.DataFrame:
    rid = vsp.FindLatestResultsID("Parasite_Drag")
    df = res2df(rid, ["Excres_Amount", "Excres_f"])
    return df


def get_parasite_refs() -> tuple[Dens, Vel, float]:
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
    vel_unit  = vsp.GetStringResults(rid, "Vinf_Label")[0]  # noqa: E221
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
            self.add(**{k: v})

    def add_parasite_refs(self, ρvS_tuple: tuple[float]):
        if len(ρvS_tuple) != 3:
            raise ValueError(
                "Tuple must have exactly 3 elements: (ρ, vel, S)")
        for k, v in zip('ρvS', ρvS_tuple):
            self.add(**{k: v})

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def __repr__(self):
        attrs = ', '.join(f'{key}={value!r}' for key, value in self.__dict__.items())  # noqa: E501
        return f'{self.__class__.__name__}({attrs})'

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def rerr(errorMgr: vsp.ErrorMgrSingleton):
    errs = [errorMgr.PopLastError().GetErrorString()
            for i in range(errorMgr.GetNumTotalErrors())][::-1]
    if errs:
        raise VspuException('\n'.join(errs))
