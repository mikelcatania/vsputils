from pathlib import Path
import pandas as pd
import unittest
import openvsp as vsp
import vsputils.vsputils as vspu
from jsonschema import ValidationError

res_dir = Path(__file__).parent.joinpath('resources')


class TestFuns(unittest.TestCase):

    def setUp(self):
        err = vsp.ErrorMgrSingleton.getInstance()
        err.SilenceErrors()

    def test_start(self):

        vspu.restart(res_dir / 'simple.vsp3')

        wid = vsp.FindGeomsWithName("Wing")

        self.assertEqual(wid[0], "FJTRPKAMIT")

    def test_restart(self):

        vspu.restart(res_dir / 'simple.vsp3')

        wid = vsp.FindGeom("Wing", 0)
        vsp.SetParmVal(wid, "Span", "XSec_1", 50.0)
        vsp.Update()

        vspu.restart(res_dir / 'simple.vsp3')
        span = vsp.GetParmVal(wid, "Span", "XSec_1")
        self.assertEqual(span, 17.0)

    def test_parse_parm_change(self):
        # Test parsing parameter change strings
        cstring = "Wing:Geom:Span:10.5"
        container, group, parm, value = vspu.parse_parm_change(cstring)
        self.assertEqual(container, "Wing")
        self.assertEqual(group, "Geom")
        self.assertEqual(parm, "Span")
        self.assertEqual(value, 10.5)

    def test_change_parm(self):
        # Test changing a parameter
        vsp_file = res_dir / "simple.vsp3"
        vspu.restart(vsp_file)
        vspu.change_parm("Wing", "XSec_1", "Span", 15.0)
        gid = vsp.FindGeom("Wing", 0)
        span = vsp.GetParmVal(gid, "Span", "XSec_1")
        self.assertEqual(span, 15.0)

    def test_res2df(self):
        # Test converting results to a DataFrame
        vsp_file = res_dir / "simple.vsp3"
        vspu.restart(vsp_file)
        vsp.ExecAnalysis("VSPAEROReadPreviousAnalysis")
        rid = vsp.FindResultsID("VSPAERO_Load", 0)
        df = vspu.res2df(rid, ["VortexSheet", "Yavg", "cl*c/cref"])
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)

    def test_change_an_input(self):
        vsp_file = res_dir / "simple.vsp3"
        vspu.restart(vsp_file)
        an = "VSPAEROSweep"
        vsp.SetAnalysisInputDefaults(an)
        vspu.change_an_input(an, "Vinf", 200.0)
        vspu.change_an_input(an, "WakeNumIter", 5)
        vspu.change_an_input(an, "WingID", "XXY")

        self.assertEqual(vsp.GetDoubleAnalysisInput(an, "Vinf")[0], 200.0)
        self.assertEqual(vsp.GetIntAnalysisInput(an, "WakeNumIter")[0], 5)
        self.assertEqual(vsp.GetStringAnalysisInput(an, "WingID")[0], "XXY")

        self.assertRaises(KeyError, vspu.change_an_input,
                          "Nonenxisting", "somepar", 50.0)
        self.assertRaises(KeyError, vspu.change_an_input,
                          "VSPAEROSweep", "nonexisting", 50.0)

    def test_get_load_results(self):
        vsp_file = res_dir / "simple.vsp3"
        vspu.restart(vsp_file)
        vsp.ExecAnalysis("VSPAEROReadPreviousAnalysis")

        df = vspu.get_load_results()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertSetEqual(set(df.columns),
                            set(["VortexSheet", "Yavg", "cl*c/cref", "cdi*c/cref",
                                 "cmyi*c/cref", "Chord", "aoa", "aoa_idx"]))

    def test_get_vspaero_refs(self):
        vsp_file = res_dir / "simple.vsp3"
        vspu.restart(vsp_file)
        vsp.ExecAnalysis("VSPAEROReadPreviousAnalysis")

        bcSxyz = vspu.get_vspaero_refs()

        self.assertTupleEqual(bcSxyz, (34.0, 3.0, 102.0, 0.0, 0.0, 0.0))

    def test_get_polar_results(self):
        vsp_file = res_dir / "simple.vsp3"
        vspu.restart(vsp_file)
        vsp.ExecAnalysis("VSPAEROReadPreviousAnalysis")

        df = vspu.get_polar_results()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertSetEqual(set(df.columns),
                            set(["Alpha", "CDi", "CDo", "CDiw", "CMiy", "CLiw"]))

    def test_parasite_drag(self):
        vsp_file = res_dir / "simple.vsp3"
        vspu.restart(vsp_file)
        vsp.ExecAnalysis("ParasiteDrag")

        df = vspu.get_geom_drag()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertSetEqual(set(df.columns),
                            set(["Comp_CD", "Comp_f", "Comp_Swet"]))

        df = vspu.get_excres_drag()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertSetEqual(set(df.columns),
                            set(["Excres_Amount", "Excres_f"]))

        self.assertEqual(vspu.get_parasite_refs(), (1.225, 102.888, 102.0))

    def tearDown(self):

        for f in res_dir.glob("*CompGeom*"):
            f.unlink()
        for f in res_dir.glob("*Parasite*"):
            f.unlink()


class TestRefs(unittest.TestCase):

    def setUp(self):
        err = vsp.ErrorMgrSingleton.getInstance()
        err.SilenceErrors()

    def test_init(self):
        r = vspu.Refs(a=3)
        self.assertEqual(r.a, 3)

        r.add(b = 34)
        r.add(b = 33)
        self.assertEqual(r.b, 33)

    def test_refs_fromaerorefs(self):
        r = vspu.Refs(j = 3)
        r.add_vspaero_refs((2, 3, 4, 5, 6, 7))
        self.assertEqual(r.b, 2)
        self.assertEqual(r.c, 3)
        self.assertEqual(r.S, 4)
        self.assertEqual(r.x, 5)
        self.assertEqual(r.y, 6)
        self.assertEqual(r.z, 7)
        self.assertEqual(r.j, 3)

    def test_refs_fromparasiterefs(self):
        r = vspu.Refs(j = 3)
        r.add_parasite_refs((1, 2, 3))
        self.assertEqual(r.ρ, 1)
        self.assertEqual(r.v, 2)
        self.assertEqual(r.S, 3)
        self.assertEqual(r.j, 3)
        
    def test_refs_fromrefs_invalid_tuple(self):
        r = vspu.Refs()
        with self.assertRaises(ValueError):
            r.add_vspaero_refs((1, 2, 3))  # Tuple with fewer than 6 elements

        with self.assertRaises(ValueError):
            r.add_parasite_refs((1, 2))  # Tuple with fewer than 3 elements
        

class TestYaml(unittest.TestCase):

    def test_valid(self):
        dct = vspu.load_yaml_dict(res_dir.joinpath('valid.yml'), validate=True)
        ref_dict = {'cases':
                    [{'name': 'somename',
                      'fname': 'ac.vsp3',
                      'changes': None,
                      'airfoils': ['cont:0:some/path', 'cont:1:some/other/path'],
                      'analyses': {'DefaultAnal': None,
                                   'AnalWithChanges':
                                   {'Alpha': 2.2, 'File': 'log.txt'}}},
                     {'name': 'another',
                      'fname': 'ad.vsp3',
                      'del_subsurf': True,
                      'changes': ['cont:gr:parm1:3.3', 'cont:gr:parm2:4.4'],
                      'analyses': {'DefaultAnal': None}}]}

        self.assertDictEqual(ref_dict, dct)

    def test_invalid(self):
        with self.assertRaises(ValidationError):
            dct = vspu.load_yaml_dict(res_dir.joinpath('invalid.yml'), validate=True)

        dct = vspu.load_yaml_dict(res_dir.joinpath('invalid.yml'), validate=False)
        ref_dict = {'cases':
                    [{'name': 'somename', 'fname': 'ac.vsp3', 'changes': None},
                     {'name': 'another',
                      'changes': ['cont:gr:parm1:3.3', 'cont:gr:parm2:4.4'],
                      'analyses': {'DefaultAnal': None}}]}
        self.assertDictEqual(ref_dict, dct)

    def test_runner(self):

        rnrs = vspu.load_yaml(res_dir.joinpath('valid.yml'))
        ref_dict = {'cases':
                    [{'name': 'somename',
                      'fname': 'ac.vsp3',
                      'changes': None,
                      'airfoils': ['cont:0:some/path', 'cont:1:some/other/path'],
                      'analyses': {'DefaultAnal': None,
                                   'AnalWithChanges':
                                   {'Alpha': 2.2, 'File': 'log.txt'}}},
                     {'name': 'another',
                      'fname': 'ad.vsp3',
                      'del_subsurf': True,
                      'changes': ['cont:gr:parm1:3.3', 'cont:gr:parm2:4.4'],
                      'analyses': {'DefaultAnal': None}}]}

        self.assertDictEqual(ref_dict['cases'][0], rnrs[0].d)
        self.assertDictEqual(ref_dict['cases'][1], rnrs[1].d)


class TestRunner(unittest.TestCase):

    def rerr(self):
        pass

if __name__ == "__main__":
    unittest.main()
