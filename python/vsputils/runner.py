from pathlib import Path
import pandas as pd
import yaml
import json
import jsonschema
from importlib.resources import files

import openvsp as vsp
import vsputils.vsputils as vspu
import vsputils.aero as vspa


class Runner:

    def __init__(self, case_dict: dict):
        self.d = case_dict
        self.name = case_dict['name']
        self.polar = pd.DataFrame()
        self.load = pd.DataFrame()
        self.geom_drag = pd.DataFrame()
        self.excres_drag = pd.DataFrame()
        self.aero_refs = vspu.Refs()
        self.parasite_refs = vspu.Refs()

        self.errorMgr = vsp.ErrorMgrSingleton.getInstance()
        self.errorMgr.SilenceErrors()

    def rerr(self):
        '''Check and raise errors'''
        vspu.rerr(self.errorMgr)

    def restart(self):
        vspu.restart(self.d['fname'])
        self.rerr()

    def change_model(self):
        changes = self.d.get('changes')
        for change in changes or []:
            c, g, p, v = vspu.parse_parm_change(change)
            vspu.change_parm(c, g, p, v)
        self.rerr()

    def change_airfoils(self):
        for af in self.d.get('airfoils', []):
            container, sec_num, fname = vspu.parse_airfoil_change(af)
            vspu.change_airfoil(container, sec_num, fname)
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
                    vspu.change_an_input(an, name, value)

            vsp.ExecAnalysis(an)

            if an == "VSPAEROSweep" or an == "VSPAEROReadPreviousAnalysis":
                self.polar = vspu.get_polar_results()
                self.load = vspu.get_load_results()
                self.aero_refs.add_vspaero_refs(vspu.get_vspaero_refs())

                xac = vspa.xac(self.polar, self.aero_refs)
                self.polar['xac'] = xac(self.polar['Alpha'])
                self.polar['CMyac'] = self.polar['CMiy'] + \
                    self.polar['CLiw'] * (self.polar['xac'] - self.aero_refs.x) / self.aero_refs.c  # noqa: E501
            if an == "ParasiteDrag":
                self.geom_drag = vspu.get_geom_drag()
                self.excres_drag = vspu.get_excres_drag()
                self.parasite_refs.add_parasite_refs(vspu.get_parasite_refs())

        vsp.DeleteAllResults()
        self.rerr()

    def run_all(self):
        self.restart()
        self.change_model()
        self.change_airfoils()
        self.del_subsurf()
        self.exec_an()

    def to_dict(self):
        return {
            'd': self.d,
            'name': self.name,
            'polar': self.polar.to_dict(orient='tight'),
            'load': self.load.to_dict(orient='tight'),
            'geom_drag': self.geom_drag.to_dict(orient='tight'),
            'excres_drag': self.excres_drag.to_dict(orient='tight'),
            'aero_refs': self.aero_refs.to_dict(),
            'parasite_refs': self.parasite_refs.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict):
        inst = cls(data['d'])
        inst.name = data['name']
        inst.polar = pd.DataFrame.from_dict(data['polar'], orient='tight')
        inst.load = pd.DataFrame.from_dict(data['load'], orient='tight')
        inst.geom_drag = pd.DataFrame.from_dict(data['geom_drag'],
                                                orient='tight')
        inst.excres_drag = pd.DataFrame.from_dict(data['excres_drag'],
                                                  orient='tight')
        inst.aero_refs = vspu.Refs.from_dict(data['aero_refs'])
        inst.parasite_refs = vspu.Refs.from_dict(data['parasite_refs'])
        return inst


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


def dump_cases(cs: list[Runner], fname: str | Path) -> None:
    with open(fname, 'w', encoding='utf8') as fp:
        json.dump([c.to_dict() for c in cs], fp, ensure_ascii=False, indent=2)


def load_cases(fname: str | Path) -> list[Runner]:
    with open(fname) as fp:
        data = json.load(fp)
    return [Runner.from_dict(d) for d in data]
