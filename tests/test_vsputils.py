from pathlib import Path
import unittest
import openvsp as vsp
import vsputils.vsputils as vspu

res_dir = Path(__file__).parent.joinpath('resources')


class TestGeom(unittest.TestCase):

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


if __name__ == "__main__":
    unittest.main()
