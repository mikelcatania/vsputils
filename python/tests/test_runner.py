import os
from pathlib import Path
import pandas as pd
import unittest
from unittest.mock import patch
import json
import tempfile
from jsonschema import ValidationError

import openvsp as vsp
import vsputils.vsputils as vspu
import vsputils.runner as vspr


res_dir = Path(__file__).parent.joinpath('resources')
cur_dir = Path.cwd()

class TestYaml(unittest.TestCase):

    def test_valid(self):
        dct = vspr.load_yaml_dict(res_dir.joinpath('valid.yml'), validate=True)
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
            dct = vspr.load_yaml_dict(res_dir.joinpath('invalid.yml'), validate=True)

        dct = vspr.load_yaml_dict(res_dir.joinpath('invalid.yml'), validate=False)
        ref_dict = {'cases':
                    [{'name': 'somename', 'fname': 'ac.vsp3', 'changes': None},
                     {'name': 'another',
                      'changes': ['cont:gr:parm1:3.3', 'cont:gr:parm2:4.4'],
                      'analyses': {'DefaultAnal': None}}]}
        self.assertDictEqual(ref_dict, dct)

    def test_runner(self):

        rnrs = vspr.load_yaml(res_dir.joinpath('valid.yml'))
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

        rnrs = vspr.load_cases(res_dir.joinpath('empty_cases.json'))
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

        rnrs = vspr.load_yaml(res_dir.joinpath('valid.yml'))
        with open(res_dir.joinpath('empty_cases.json')) as fp:
            ref_cs = json.load(fp)
        with tempfile.NamedTemporaryFile(delete=True) as tf:
            vspr.dump_cases(rnrs, tf.name)
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

        c = vspr.Runner(cd)
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
        rnr = vspr.Runner.from_dict(cs[0])
        self.assertDictEqual(rnr.to_dict(), cs[0])

    def test_funs(self):

        rnrs = vspr.load_yaml(res_dir.joinpath('runner.yaml'))
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

            rnr = vspr.Runner(cd)

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
        # The parasite ref values depend on how the test is run. If a vsp3 file has
        # been loaded previously in the tests, it needs to be set to the values of
        # that file. VSPRenew apparenlty does not set the parasite drag tool values to
        # any global default.
        ref_para_ref.add_parasite_refs((0.6526823360748901, 152.4, 100.0))
        self.assertFalse(rnr.polar.empty)
        self.assertFalse(rnr.load.empty)
        self.assertEqual(rnr.aero_refs, ref_aero_ref)
        self.assertFalse(rnr.geom_drag.empty)
        self.assertFalse(rnr.excres_drag.empty)
        self.assertEqual(rnr.parasite_refs, ref_para_ref)

    def test_run_all(self):

        rnr = vspr.Runner({'name': 'somename'})
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
