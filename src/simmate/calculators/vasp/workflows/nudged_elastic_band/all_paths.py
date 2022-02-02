# -*- coding: utf-8 -*-

"""
Runs a NEB on all unique pathways within a structure. 

The folder tree looks like...
```
simmate-task-12345/  # determined by simmate.utilities.get_directory
    ├── bulk_relaxation
    ├── bulk_static_energy
    ├── migration_hop_00
    ├── migration_hop_01
    ...
    └── migration_hop_N  # all migration_hop folders have the same structure
        ├── endpoint_relaxation_start
        ├── endpoint_relaxation_end
        ├── 01
        ├── 02
        ├── 03
        ...
        └── N  # corresponds to image number
```
"""

import os

from simmate.workflow_engine.workflow import (
    Workflow,
    Parameter,
    ModuleStorage,
)
from simmate.workflows.common_tasks import (
    LoadInputAndRegister,
    parse_multi_command,
)
from simmate.calculators.vasp.workflows.nudged_elastic_band.utilities import (
    BuildDiffusionAnalysisTask,
)
from simmate.calculators.vasp.workflows.relaxation import (
    mit_workflow as relaxation_mit_workflow,
)
from simmate.calculators.vasp.workflows.energy import (
    mit_workflow as energy_mit_workflow,
)

from simmate.calculators.vasp.database.nudged_elastic_band import (
    MITDiffusionAnalysis,
)

# Convert our workflow objects to task objects
relax_bulk = relaxation_mit_workflow.to_workflow_task()
energy_bulk = energy_mit_workflow.to_workflow_task()


# Extra setup tasks
load_input_and_register = LoadInputAndRegister()  # TODO: make DiffusionAnalysis a calc?
build_db = BuildDiffusionAnalysisTask(MITDiffusionAnalysis)

with Workflow("NEB (for all unique pathways)") as workflow:

    structure = Parameter("structure")
    migrating_specie = Parameter("migrating_specie")
    source = Parameter("source", default=None)
    directory = Parameter("directory", default=None)
    # assume use_previous_directory=False for this flow

    # I separate these out because each calculation is a very different scale.
    # For example, you may want to run the bulk relaxation on 10 cores, the
    # supercell on 50, and the NEB on 200. Even though more cores are available,
    # running smaller calculation on more cores could slow down the calc.
    command = Parameter("command", default="vasp_std > vasp.out")
    # command list expects three subcommands:
    #   command_bulk, command_supercell, and command_neb
    subcommands = parse_multi_command(
        command,
        commands_out=["command_bulk", "command_supercell", "command_neb"],
    )

    # Load our input and make a base directory for all other workflows to run
    # within for us.
    structure_toolkit, directory_cleaned = load_input_and_register(
        input_obj=structure,
        source=source,
        directory=directory,
    )

    # Our step is to run a relaxation on the bulk structure and it uses our inputs
    # directly. The remaining one tasks pass on results.
    run_id_00 = relax_bulk(
        structure=structure_toolkit,
        command=subcommands["command_bulk"],
        directory=directory_cleaned + os.path.sep + "bulk_relaxation",
    )

    # A static energy calculation on the relaxed structure. This isn't necessarily
    # required for NEB, but it takes very little time.
    # run_id_01 = energy_bulk(
    #     structure={
    #         "calculation_table": "MITRelaxation",
    #         "directory": run_id_00["directory"],
    #         "structure_field": "structure_final",
    #     },
    #     command=subcommands["command_bulk"],
    #     directory=directory_cleaned + os.path.sep + "bulk_static_energy",
    # )

    # This step does NOT run any calculation, but instead, identifies all
    # diffusion pathways and builds the necessary database entries.
    migration_hop_ids = build_db(
        structure=structure_toolkit,  # TODO: I'm using toolkit for quick testing
        # structure={
        #     "calculation_table": "MITStaticEnergy",
        #     "directory": run_id_01["directory"],
        #     "structure_field": "structure_final",
        # },
        migrating_specie=migrating_specie,
        directory=directory_cleaned,
        vacancy_mode=True,  # assumed for now
    )

workflow.storage = ModuleStorage(__name__)
workflow.project_name = "Simmate-Diffusion"
