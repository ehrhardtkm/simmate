# -*- coding: utf-8 -*-

import json
from pathlib import Path

from simmate.apps.vasp.inputs import Incar
from simmate.engine import ErrorHandler
from simmate.toolkit import Structure


class RealOptlay(ErrorHandler):
    """
    This handler addresses a series of warning messages that each have the same
    attempted fixes. There are a series of fixes that can be attempted, so we
    keep a running log of how many times this handler is called.
    """

    # NOTE: I call this RealOptlay but don't have a good understanding of what
    # the error exactly is. This is simply a conversion from Custodian of the
    # following errors: ["rspher", "real_optlay", "nicht_konv"]

    is_monitor = True
    filename_to_check = "vasp.out"
    possible_error_messages = [
        "ERROR RSPHER",
        "REAL_OPTLAY: internal error",
        "REAL_OPT: internal ERROR",
        "ERROR: SBESSELITER : nicht konvergent",
    ]

    # Number of atoms in a lattice to consider this a large cell. This affects
    # how we treat the error and correct it.
    natoms_large_cell = 100

    def correct(self, directory: Path) -> str:

        # load the INCAR file to view the current settings
        incar_filename = directory / "INCAR"
        incar = Incar.from_file(incar_filename)

        # load the error-count file if it exists
        error_count_filename = directory / "simmate_error_counts.json"
        if error_count_filename.exists():
            with error_count_filename.open() as error_count_file:
                error_counts = json.load(error_count_file)
        # otherwise we are starting with an empty dictionary
        else:
            error_counts = {}

        # The fix is based on the number of times we've already tried to
        # fix this. So let's make sure it's in our error_count dictionary.
        # If it isn't there yet, set the count to 0 and we'll update it below.
        error_counts["real_optlay"] = error_counts.get("real_optlay", 0)

        poscar_filename = directory / "POSCAR"
        structure = Structure.from_file(poscar_filename)

        if structure.num_sites < self.natoms_large_cell:
            incar["LREAL"] = False
            correction = "set LREAL to False"

        else:
            # for large supercell, try an in-between option LREAL = True
            # prior to LREAL = False
            if error_counts["real_optlay"] == 0:
                # use real space projectors generated by pot
                incar["LREAL"] = True
                correction = "set LREAL to True"
            elif error_counts["real_optlay"] == 1:
                incar["LREAL"] = False
                correction = "set LREAL to False"
            # increase our attempt count
            error_counts["real_optlay"] += 1

        # rewrite the INCAR with new settings
        incar.to_file(incar_filename)

        # rewrite the new error count file
        with error_count_filename.open("w") as file:
            json.dump(error_counts, file)

        # now return the correction made for logging
        return correction
