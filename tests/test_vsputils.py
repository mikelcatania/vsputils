from pathlib import Path
import pandas as pd
import unittest
import openvsp as vsp
import vsputils.vsputils as vspu

res_dir = Path(__file__).parent.joinpath('resources')


class TestGeom(unittest.TestCase):

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
        df = vspu.res2df(rid, ["WingId", "Yavg", "cl*c/cref"])
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
                            set(["WingId", "Yavg", "cl*c/cref", "cd*c/cref",
                                 "cmy*c/cref", "aoa", "aoa_idx"]))

    def test_get_polar_results(self):
        vsp_file = res_dir / "simple.vsp3"
        vspu.restart(vsp_file)
        vsp.ExecAnalysis("VSPAEROReadPreviousAnalysis")

        df = vspu.get_polar_results()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertSetEqual(set(df.columns),
                            set(["Alpha", "CDi", "CDo", "CDt", "CMy", "CL"]))

    def test_parasitic_drag(self):
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

        self.assertEqual(vspu.get_parasite_sref(), 102.0)

    def tearDown(self):

        for f in res_dir.glob("*CompGeom*"):
            f.unlink()
        for f in res_dir.glob("*Parasite*"):
            f.unlink()


if __name__ == "__main__":
    unittest.main()
