import numpy as np
from numpy.polynomial import Polynomial
from numpy import ndarray
import pandas as pd
from spq.spq.aero import Vel
from collections.abc import Callable
from scipy.optimize import curve_fit
import vsputils.vsputils as vspu

def drag_polar(polar: pd.DataFrame, with_cdo: bool = False) -> Polynomial:

    cdi_pol = Polynomial.fit(polar['CLiw'], polar['CDiw'], 2)

    if with_cdo:
        cdo_pol = Polynomial.fit(polar['CLiw'], polar['CDo'], 2)
        min_cdo_cl = cdo_pol.deriv().roots()[0]
        cdi_pol = cdi_pol + cdo_pol - cdo_pol(min_cdo_cl)
    
    return cdi_pol.convert()


def parasite_drag(v: ndarray[Vel], cd0: ndarray[float]) -> Callable[[ndarray[Vel]], ndarray[float]]:

    def inv_power(x, a, b):
        return a / (x**b)

    r, c = curve_fit(inv_power, v, cd0)

    def inv_p(x):
        return r[0] / (x ** r[1])
    return inv_p
    
    
def xac(polar: pd.DataFrame, aero_refs: vspu.Refs) -> Polynomial:

    a = polar['Alpha']
    cl = polar['CLiw']
    cm = polar['CMiy']

    clp = Polynomial.fit(a, cl, 2)
    cmp = Polynomial.fit(a, cm, 2)

    xac = -(Polynomial.fit(a, cmp.deriv()(a)/clp.deriv()(a), 2)) * aero_refs.c + aero_refs.x
    return xac.convert()
