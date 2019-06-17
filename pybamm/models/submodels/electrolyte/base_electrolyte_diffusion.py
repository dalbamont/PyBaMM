#
# Base class for electrolyte diffusion
#
import pybamm
import autograd.numpy as np


class BaseElectrolyteDiffusion(pybamm.BaseSubModel):
    """Base class for conservation of mass in the electrolyte.

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel

    *Extends:* :class:`pybamm.BaseSubModel`
    """

    def __init__(self, param):
        super().__init__(param)

    def _get_standard_concentration_variables(self, c_e, c_e_av):

        c_e_typ = self.param.c_e_typ
        c_e_n, c_e_s, c_e_p = c_e.orphans

        variables = {
            "Electrolyte concentration": c_e,
            "Electrolyte concentration [mol.m-3]": c_e_typ * c_e,
            "Average electrolyte concentration": c_e_av,
            "Average electrolyte concentration [mol.m-3]": c_e_typ * c_e_av,
            "Negative electrolyte concentration": c_e_n,
            "Negative electrolyte concentration [mol.m-3]": c_e_typ * c_e_n,
            "Separator electrolyte concentration": c_e_s,
            "Separator electrolyte concentration [mol.m-3]": c_e_typ * c_e_s,
            "Positive electrolyte concentration": c_e_p,
            "Positive electrolyte concentration [mol.m-3]": c_e_typ * c_e_p,
        }

        return variables

    def _get_standard_flux_variables(self, N_e):

        param = self.param
        D_e_typ = param.D_e(param.c_e_typ)
        flux_scale = D_e_typ * param.c_e_typ / param.L_x

        variables = {
            "Electrolyte flux": N_e,
            "Electrolyte flux [mol.m-2.s-1]": N_e * flux_scale,
        }

        return variables

    def set_events(self, variables):
        c_e = variables["Electrolyte concentration"]
        self.events = [pybamm.Function(np.min, c_e) - 0.002]

