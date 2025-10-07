import os
from pathlib import Path
import pandas as pd
from numpy.polynomial import Polynomial
import numpy.testing
import unittest
from unittest.mock import patch
import json
import tempfile
import openvsp as vsp
import vsputils.vsputils as vspu
import vsputils.aero as vspa
import vsputils.runner as vspr
from jsonschema import ValidationError

res_dir = Path(__file__).parent.joinpath('resources')
cur_dir = Path.cwd()


class TestDrag(unittest.TestCase):

    def test_polar(self):

        rnrs = vspr.load_cases(res_dir.joinpath('cases.json'))
        p = rnrs[0].polar

        cdi  = vspa.drag_polar(p)
        cdio = vspa.drag_polar(p, with_cdo=True)

        expected_cdi  = Polynomial([-2.06392658e-06, -2.17396057e-05,  2.94595394e-02])
        expected_cdio = Polynomial([-2.01588016e-06,  1.00050586e-05,  3.47030301e-02])

        numpy.testing.assert_allclose(cdi.coef, expected_cdi.coef)
        numpy.testing.assert_allclose(cdio.coef, expected_cdio.coef)

    def test_parasite(self):

        vels = [20.5776, 27.4368, 34.29600000000001, 41.1552, 48.01440000000001,
                54.8736, 61.7328, 68.59200000000001, 75.45120000000001, 82.3104]
        cd0s = [0.02624567, 0.02521113, 0.02445641, 0.02386864, 0.02339087,
                0.0229906 , 0.02264764, 0.02234863, 0.02208432, 0.02184803]

        cd0 = vspa.parasite_drag(vels, cd0s)

        ref_vels = [10, 20, 50, 100]
        ref_cd0s = [0.02881764, 0.02629413, 0.02329413, 0.02125431]
        numpy.testing.assert_allclose(cd0(ref_vels), ref_cd0s, rtol=3e-7)


class TestAC(unittest.TestCase):

    def test_xac(self):

        rnrs = vspr.load_cases(res_dir.joinpath('cases.json'))
        p = rnrs[0].polar
        r = rnrs[0].aero_refs

        xac = vspa.xac(p, r)

        expected_xac = Polynomial([ 1.77776623e+00, -1.70610385e-03, -1.39098698e-06])

        numpy.testing.assert_allclose(xac.coef, expected_xac.coef)
