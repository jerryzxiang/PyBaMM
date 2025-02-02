#
# Class for electron-migration limited SEI growth
#
import pybamm
from .base_sei import BaseModel


class ElectronMigrationLimited(BaseModel):
    """
    Class for electron-migration limited SEI growth.

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel
    reaction_loc : str
        Where the reaction happens: "x-average" (SPM, SPMe, etc),
        "full electrode" (full DFN), or "interface" (half-cell DFN)
    options : dict, optional
        A dictionary of options to be passed to the model.

    **Extends:** :class:`pybamm.sei.BaseModel`
    """

    def __init__(self, param, reaction_loc, options=None):
        super().__init__(param, options=options)
        self.reaction_loc = reaction_loc

    def get_fundamental_variables(self):
        if self.reaction_loc == "x-average":
            L_inner_av = pybamm.standard_variables.L_inner_av
            L_outer_av = pybamm.standard_variables.L_outer_av
            L_inner = pybamm.PrimaryBroadcast(L_inner_av, "negative electrode")
            L_outer = pybamm.PrimaryBroadcast(L_outer_av, "negative electrode")
        elif self.reaction_loc == "full electrode":
            L_inner = pybamm.standard_variables.L_inner
            L_outer = pybamm.standard_variables.L_outer
        elif self.reaction_loc == "interface":
            L_inner = pybamm.standard_variables.L_inner_interface
            L_outer = pybamm.standard_variables.L_outer_interface

        variables = self._get_standard_thickness_variables(L_inner, L_outer)
        variables.update(self._get_standard_concentration_variables(variables))

        return variables

    def get_coupled_variables(self, variables):
        L_sei_inner = variables["Inner SEI thickness"]
        if self.reaction_loc == "interface":
            phi_s_n = variables["Lithium metal interface electrode potential"]
        else:
            phi_s_n = variables["Negative electrode potential"]

        U_inner = self.param.U_inner_electron
        C_sei = self.param.C_sei_electron

        j_sei = (phi_s_n - U_inner) / (C_sei * L_sei_inner)

        alpha = 0.5
        j_inner = alpha * j_sei
        j_outer = (1 - alpha) * j_sei

        variables.update(self._get_standard_reaction_variables(j_inner, j_outer))

        # Update whole cell variables, which also updates the "sum of" variables
        variables.update(super().get_coupled_variables(variables))

        return variables

    def set_rhs(self, variables):
        if self.reaction_loc == "x-average":
            L_inner = variables["X-averaged inner SEI thickness"]
            L_outer = variables["X-averaged outer SEI thickness"]
            j_inner = variables["X-averaged inner SEI interfacial current density"]
            j_outer = variables["X-averaged outer SEI interfacial current density"]
            # Note a is dimensionless (has a constant value of 1 if the surface
            # area does not change)
            a = variables["X-averaged negative electrode surface area to volume ratio"]
        else:
            L_inner = variables["Inner SEI thickness"]
            L_outer = variables["Outer SEI thickness"]
            j_inner = variables["Inner SEI interfacial current density"]
            j_outer = variables["Outer SEI interfacial current density"]
            if self.reaction_loc == "interface":
                a = 1
            else:
                a = variables["Negative electrode surface area to volume ratio"]

        v_bar = self.param.v_bar
        Gamma_SEI = self.param.Gamma_SEI

        self.rhs = {
            L_inner: -Gamma_SEI * a * j_inner,
            L_outer: -v_bar * Gamma_SEI * a * j_outer,
        }

    def set_initial_conditions(self, variables):
        if self.reaction_loc == "x-average":
            L_inner = variables["X-averaged inner SEI thickness"]
            L_outer = variables["X-averaged outer SEI thickness"]
        else:
            L_inner = variables["Inner SEI thickness"]
            L_outer = variables["Outer SEI thickness"]

        L_inner_0 = self.param.L_inner_0
        L_outer_0 = self.param.L_outer_0

        self.initial_conditions = {L_inner: L_inner_0, L_outer: L_outer_0}
