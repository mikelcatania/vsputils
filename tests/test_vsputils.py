import os
from pathlib import Path
import pandas as pd
import unittest
from unittest.mock import patch
import json
import tempfile
import openvsp as vsp
import vsputils.vsputils as vspu
from jsonschema import ValidationError

res_dir = Path(__file__).parent.joinpath('resources')
cur_dir = Path.cwd()

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

        # Expected error, because the analysis did not exist.
        err = vsp.ErrorMgrSingleton.getInstance()
        self.assertRaises(vspu.VspuException, vspu.rerr, err)

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

    def test_dict(self):
        dct = {'a': 3, 'b': 5}
        r = vspu.Refs.from_dict(dct)
        self.assertEqual(r.a, 3)
        self.assertEqual(r.b, 5)
        self.assertDictEqual(r.to_dict(), dct)

    def test_eq(self):
        ra = vspu.Refs()
        rb = vspu.Refs()
        self.assertTrue(ra == rb)
        ra = vspu.Refs(g=3)
        rb = vspu.Refs(g=3)
        self.assertTrue(ra == rb)
        rb.add(h=5)
        self.assertFalse(ra == rb)
        ra = vspu.Refs(g=5)
        rb = vspu.Refs(h=6)
        self.assertFalse(ra == rb)
        

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


class TestJson(unittest.TestCase):

    def test_load(self):

        rnrs = vspu.load_cases(res_dir.joinpath('empty_cases.json'))
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
        empty_ref = vspu.Refs()

        self.assertDictEqual(ref_dict['cases'][0], rnrs[0].d)
        self.assertDictEqual(ref_dict['cases'][1], rnrs[1].d)
        self.assertTrue(rnrs[0].polar.empty)
        self.assertTrue(rnrs[1].polar.empty)
        self.assertTrue(rnrs[0].load.empty)
        self.assertTrue(rnrs[1].load.empty)
        self.assertTrue(rnrs[0].geom_drag.empty)
        self.assertTrue(rnrs[1].geom_drag.empty)
        self.assertTrue(rnrs[0].excres_drag.empty)
        self.assertTrue(rnrs[1].excres_drag.empty)
        self.assertTrue(rnrs[0].aero_refs == empty_ref)
        self.assertTrue(rnrs[1].aero_refs == empty_ref)
        self.assertTrue(rnrs[0].parasite_refs == empty_ref)
        self.assertTrue(rnrs[1].parasite_refs == empty_ref)

    def test_dump(self):

        rnrs = vspu.load_yaml(res_dir.joinpath('valid.yml'))
        with open(res_dir.joinpath('empty_cases.json')) as fp:
            ref_cs = json.load(fp)
        with tempfile.NamedTemporaryFile(delete=True) as tf:
            vspu.dump_cases(rnrs, tf.name)
            tf.flush()
            tf.seek(0)

            cs = json.load(tf)
            for it, rit in zip(cs, ref_cs):
                self.assertDictEqual(it, rit)
            




class TestRunner(unittest.TestCase):

    def test_init(self):

        cd = {'name': 'somename',
              'fname': 'ac.vsp3',
              'changes': None,
              'airfoils': ['cont:0:some/path', 'cont:1:some/other/path'],
              'analyses': {'DefaultAnal': None,
                           'AnalWithChanges':
                           {'Alpha': 2.2, 'File': 'log.txt'}}}

        c = vspu.Runner(cd)
        empty_ref = vspu.Refs()

        self.assertDictEqual(c.d, cd)
        self.assertEqual(c.name, 'somename')
        self.assertTrue(c.polar.empty)
        self.assertTrue(c.load.empty)
        self.assertTrue(c.geom_drag.empty)
        self.assertTrue(c.excres_drag.empty)
        self.assertTrue(c.aero_refs == empty_ref)
        self.assertTrue(c.parasite_refs == empty_ref)

    def test_dict(self):

        with open(res_dir.joinpath('cases.json')) as fp:
            cs = json.load(fp)
        rnr = vspu.Runner.from_dict(cs[0])
        self.assertDictEqual(rnr.to_dict(), cs[0])

    def test_funs(self):

        rnrs = vspu.load_yaml(res_dir.joinpath('runner.yaml'))
        rnrs[0].d['fname'] = res_dir.joinpath('simple.vsp3').resolve()
        rnr = rnrs[0]
        rnr.restart()

        rnr.change_model()
        gid = vsp.FindGeom("Wing", 0)
        span = vsp.GetParmVal(gid, "Span", "XSec_1")
        self.assertEqual(span, 50.0)

        rnr.del_subsurf()
        self.assertEqual(vsp.GetAllSubSurfIDs(), ())

    def test_exec(self):

        temp_aero_file = tempfile.NamedTemporaryFile(delete=False)
        temp_para_file = tempfile.NamedTemporaryFile(delete=False)

        try:
            cd = {'name': 'somename', 'fname': 'void.vsp3',
                  'analyses': {
                      'VSPAEROComputeGeometry': {
                          'ThinGeomSet': 1,
                          'GeomSet': -1
                      },
                      'VSPAEROSweep': {
                          'ThinGeomSet': 1,
                          'GeomSet': -1,
                          'RedirectFile': temp_aero_file.name,
                          'AlphaNpts': 1,
                          'AlphaStart': 2
                      },
                      'ParasiteDrag': {
                          'FileName': temp_para_file.name,
                          'GeomSet': 3
                      }
                  }
                  }

            rnr = vspu.Runner(cd)

            # Gonna start from scratch.
            vsp.VSPRenew()
            wid = vsp.AddGeom('WING')
            vsp.Update()
            vsp.SetSetFlag(wid, 3, True);
            vsp.Update()
            vsp.AddExcrescence("Something", vsp.EXCRESCENCE_CD, 0.0003);
            vsp.Update()

            rnr.exec_an()

        finally:
            os.remove(temp_aero_file.name)
            os.remove(temp_para_file.name)

        ref_aero_ref = vspu.Refs()
        ref_aero_ref.add_vspaero_refs((1.0, 1.0, 100.0, 0.0, 0.0, 0.0))
        ref_para_ref = vspu.Refs()
        # If the test is done only for this function, the following ref will fail.
        # The ref is done to match a previously loaded vsp3 file. VSPRenew
        # apparenlty does not set the parasite drag tool values to any global default.
        ref_para_ref.add_parasite_refs((1.225, 102.888, 102.0))
        self.assertFalse(rnr.polar.empty)
        self.assertFalse(rnr.load.empty)
        self.assertEqual(rnr.aero_refs, ref_aero_ref)
        self.assertFalse(rnr.geom_drag.empty)
        self.assertFalse(rnr.excres_drag.empty)
        self.assertEqual(rnr.parasite_refs, ref_para_ref)

    def test_run_all(self):

        rnr = vspu.Runner({'name': 'somename'})
        with patch.object(rnr, 'restart') as mock_restart,\
             patch.object(rnr, 'change_model') as mock_change_model,\
             patch.object(rnr, 'change_airfoils') as mock_change_airfoils,\
             patch.object(rnr, 'del_subsurf') as mock_del_subsurf,\
             patch.object(rnr, 'exec_an') as mock_exec_an:

            rnr.run_all()

            mock_restart.assert_called_once()
            mock_change_model.assert_called_once()
            mock_change_airfoils.assert_called_once()
            mock_del_subsurf.assert_called_once()
            mock_exec_an.assert_called_once()
            
        
    def tearDown(self):

        for f in cur_dir.glob("Unnamed*"):
            f.unlink()
        
        
        

if __name__ == "__main__":
    unittest.main()
