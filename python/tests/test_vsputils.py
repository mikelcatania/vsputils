from pathlib import Path
import pandas as pd
import unittest
import openvsp as vsp
import vsputils.vsputils as vspu

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
        

if __name__ == "__main__":
    unittest.main()
