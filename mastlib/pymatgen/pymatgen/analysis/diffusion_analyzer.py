#!/usr/bin/env python

"""
A module to perform diffusion analyses (e.g. calculating diffusivity from
mean square displacements etc.). If you use this module,
please consider citing the following papers::

    Ong, S. P., Mo, Y., Richards, W. D., Miara, L., Lee, H. S., & Ceder, G.
    (2013). Phase stability, electrochemical stability and ionic conductivity
    of the Li10+-1MP2X12 (M = Ge, Si, Sn, Al or P, and X = O, S or Se) family
    of superionic conductors. Energy & Environmental Science, 6(1), 148.
    doi:10.1039/c2ee23355j

    Mo, Y., Ong, S. P., & Ceder, G. (2012). First Principles Study of the
    Li10GeP2S12 Lithium Super Ionic Conductor Material. Chemistry of Materials,
    24(1), 15-17. doi:10.1021/cm203303y
"""

from __future__ import division

__author__ = "Will Richards"
__version__ = "0.1"
__maintainer__ = "Will Richards"
__email__ = "wrichard@mit.edu"
__status__ = "Beta"
__date__ = "5/2/13"


import numpy as np

from pymatgen.core import Structure, smart_element_or_specie
from pymatgen.core.physical_constants import AVOGADROS_CONST, BOLTZMANN_CONST,\
    ELECTRON_CHARGE
from pymatgen.serializers.json_coders import MSONable
from pymatgen.io.vaspio.vasp_output import Vasprun


class DiffusionAnalyzer(MSONable):
    """
    Class for performing diffusion analyses.

    .. attribute: diffusivity

        Diffusivity in cm^2 / cm

    .. attribute: conductivity

        Conductivity in mS / cm

    .. attribute: diffusivity_components

        A vector with diffusivity in the a, b and c directions in cm^2 / cm

    .. attribute: conductivity components

        A vector with conductivity in the a, b and c directions in mS / cm

    .. attribute: max_framework_displacement

        The maximum (drift adjusted) distance of any framework atom from its
        starting location in A

    """

    def __init__(self, structure, displacements, specie, temperature,
                 time_step, step_skip=10, max_dt=0.7):
        """
        This constructor is meant to be used with pre-processed data.
        Other convenient constructors are provided as static methods, e.g.,
        see from_vaspruns.

        Args:
            structure:
                Initial structure.
            displacements:
                Numpy array of with shape [site, time step, axis]
            specie:
                Specie to calculate diffusivity for as a String. E.g., "Li".
            temperature:
                Temperature of the diffusion run in Kelvin.
            time_step:
                Time step between measurements.
            step_skip:
                Sampling frequency of the displacements (time_step is
                multiplied by this number to get the real time between
                measurements)
            max_dt:
                maximum fraction of the total run time to use when
                calculating MSD vs dt. Typical values are between 0.1-1.
                If 0.1, the highest time interval will have 10 uncorrelated
                samplings. If 1, there will only be one sampling at this
                maximum dt.
        """
        self.s = structure
        self.disp = displacements
        self.sp = specie
        self.temperature = temperature
        self.time_step = time_step
        self.step_skip = step_skip
        self.max_dt = max_dt
        self.indices = []
        self.framework_indices = []
        for i, site in enumerate(structure):
            if site.specie.symbol == specie:
                self.indices.append(i)
            else:
                self.framework_indices.append(i)
        if self.disp.shape[1] < 2:
            self.diffusivity = 0.
            self.conductivity = 0.
            self.diffusivity_components = np.array([0., 0., 0.])
            self.conductivity_components = np.array([0., 0., 0.])
            self.max_framework_displacement = 0
        else:
            framework_disp = self.disp[self.framework_indices]
            drift = np.average(framework_disp, axis=0)[None, :, :]
            #drift corrected position
            dc_x = self.disp[self.indices] - drift
            dc_framework = self.disp[self.framework_indices] - drift
            self.max_framework_displacement = \
                np.max(np.sum(dc_framework ** 2, axis=-1) ** 0.5)
            df_x = self.s.lattice.get_fractional_coords(dc_x)
            #limit the number of sampled timesteps to 200
            timesteps = np.arange(10, int(max_dt * dc_x.shape[1]),
                                  max(dc_x.shape[1] / 200, 1))
            x = timesteps * self.time_step * self.step_skip

            #calculate the smoothed msd values
            s_msd = np.zeros_like(x, dtype=np.double)
            s_msd_components = np.zeros(x.shape + (3,))
            lengths = np.array(self.s.lattice.abc)[None, None, :]
            for i, n in enumerate(timesteps):
                dx = dc_x[:, n:, :] - dc_x[:, :-n, :]
                s_msd[i] = 3 * np.average(dx ** 2)
                dcomponents = (df_x[:, n:, :] - df_x[:, :-n, :]) * lengths
                s_msd_components[i] = np.average(np.average(dcomponents ** 2,
                                                            axis=1), axis=0)

            #run the regression on the msd components
            m_components = np.zeros(3)
            for i in range(3):
                a = np.ones((len(x), 2))
                a[:, 0] = x
                (m, c), res, rank, s = \
                    np.linalg.lstsq(a, s_msd_components[:, i])
                m_components[i] = max(m, 1e-15)

            a = np.ones((len(x), 2))
            a[:, 0] = x
            (m, c), res, rank, s = np.linalg.lstsq(a, s_msd)
            #m shouldn't be negative
            m = max(m, 1e-20)

            #factor of 10 is to convert from A^2/fs to cm^2/s
            #factor of 6 is for dimensionality
            conv_factor = get_conversion_factor(self.s, self.sp,
                                                self.temperature)
            self.diffusivity = m / 60
            self.conductivity = self.diffusivity * conv_factor

            self.diffusivity_components = m_components / 20
            self.conductivity_components = self.diffusivity_components * \
                conv_factor

    @classmethod
    def from_vaspruns(cls, vaspruns, specie, max_dt=0.7):
        """
        Convenient constructor that takes in a list of Vasprun objects to
        perform diffusion analysis.

        Args:
            vaspruns:
                list of Vasprun objects (must be ordered in sequence of run).
                 E.g., you may have performed sequential VASP runs to obtain
                 sufficient statistics.
            specie:
                Specie to calculate diffusivity for as a String. E.g., "Li".
            max_dt:
                maximum fraction of the total run time to use when
                calculating MSD vs dt. Typical values are between 0.1-1.
                If 0.1, the highest time interval will have 10 uncorrelated
                samplings. If 1, there will only be one sampling at this
                maximum dt.
        """
        structure = vaspruns[0].initial_structure
        step_skip = vaspruns[0].ionic_step_skip

        p = []
        for vr in vaspruns:
            assert vr.ionic_step_skip == step_skip
            p.extend([np.array(s['structure'].frac_coords)[:, None]
                      for s in vr.ionic_steps])
        p = np.concatenate(p, axis=1)
        dp = p[:, 1:] - p[:, :-1]
        dp = np.concatenate([np.zeros_like(dp[:, (0,)]), dp], axis=1)
        dp = dp - np.round(dp)
        f_disp = np.cumsum(dp, axis=1)
        disp = structure.lattice.get_cartesian_coords(f_disp)

        temperature = vaspruns[0].parameters['TEEND']
        time_step = vaspruns[0].parameters['POTIM']

        return cls(structure, disp, specie, temperature,
                   time_step, step_skip=step_skip, max_dt=max_dt)

    @classmethod
    def from_files(cls, filepaths, specie, step_skip=10, ncores=None):
        """
        Convenient constructor that takes in a list of vasprun.xml paths to
        perform diffusion analysis.

        Args:
            filepaths:
                List of paths to vasprun.xml files of runs. (must be
                ordered in sequence of run). For example,
                you may have done sequential VASP runs and they are in run1,
                run2, run3, etc. You should then pass in
                ["run1/vasprun.xml", "run2/vasprun.xml", ...].
            specie:
                Specie to calculate diffusivity for as a String. E.g., "Li".
            step_skip:
                Sampling frequency of the displacements (time_step is
                multiplied by this number to get the real time between
                measurements). E.g., you may not want to sample every single
                time step.
            ncores:
                Numbers of cores to use for multiprocessing. Can speed up
                vasprun parsing considerable. Defaults to None,
                which means serial.
        """
        func = map
        if ncores is not None:
            import multiprocessing
            p = multiprocessing.Pool(ncores)
            func = p.map
        vaspruns = func(_get_vasprun, [(p, step_skip) for p in filepaths])
        return cls.from_vaspruns(vaspruns, specie=specie)

    @property
    def to_dict(self):
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "structure": self.s.to_dict,
            "displacements": self.disp.tolist(),
            "specie": self.sp,
            "temperature": self.temperature,
            "time_step": self.time_step,
            "step_skip": self.step_skip,
            "max_dt": self.max_dt
        }

    @classmethod
    def from_dict(cls, d):
        structure = Structure.from_dict(d["structure"])
        return cls(structure, np.array(d["displacements"]), specie=d["specie"],
                   temperature=d["temperature"], time_step=d["time_step"],
                   step_skip=d["step_skip"], max_dt=d["max_dt"])


def get_conversion_factor(structure, species, temperature):
    """
    Conversion factor to convert between cm^2/s diffusivity measurements and
    mS/cm conductivity measurements based on number of atoms of diffusing
    species. Note that the charge is based on the oxidation state of the
    species (where available), or else the number of valence electrons
    (usually a good guess, esp for main group ions).

    Args:
        structure:
            Input structure.
        species:
            Diffusing species.
        temperature:
            Temperature of the diffusion run in Kelvin.

    Returns:
        Conversion factor.
        Conductivity (in mS/cm) = Conversion Factor * Diffusivity (in cm^2/s)
    """
    df_sp = smart_element_or_specie(species)
    if hasattr(df_sp, "oxi_state"):
        z = df_sp.oxi_state
    else:
        z = df_sp.full_electronic_structure[-1][2]

    n = structure.composition[species]

    V = structure.volume * 1e-24  # units cm^3
    F = ELECTRON_CHARGE * AVOGADROS_CONST  # sA/mol
    return 1000 * n / (V * AVOGADROS_CONST) * z ** 2 * F ** 2\
        / (BOLTZMANN_CONST * AVOGADROS_CONST * temperature)


def _get_vasprun(args):
    return Vasprun(args[0], ionic_step_skip=args[1])