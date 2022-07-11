# -*- coding: utf-8 -*-

import json
import cloudpickle
import yaml
import re
from typing import List
from functools import cache  # cached_property doesnt work with classmethod

from prefect.tasks import task  # present only for convience imports elsewhere
from prefect.flows import Flow
from prefect.states import State
from prefect.context import FlowRunContext
from prefect.client import get_client
from prefect.orion.schemas.filters import FlowFilter, FlowRunFilter
from prefect.packaging import OrionPackager
from prefect.packaging.serializers import PickleSerializer

import simmate
from simmate.toolkit import Structure
from simmate.database.base_data_types import Calculation
from simmate.workflow_engine import S3Task
from simmate.utilities import async_to_sync


class Workflow:
    """
    This class behaves exactly like a normal Prefect workflow, where we add some
    common utilities and pre-submit tasks. For example, there is the `run_cloud`
    method, which allows us to register a calculation to a database table before
    we submit the workflow to Prefect Cloud.

    To learn how to use this class, see
    [prefect.core.flow.Flow](https://docs.prefect.io/api/latest/core/flow.html#flow-2)
    """

    # TODO: set storage attribute to module

    # TODO: inherit doc from s3task
    # by default we just copy the docstring of the S3task to the workflow
    # workflow.__doc__ = s3task.__doc__

    version: str = simmate.__version__
    """
    Version number for this flow. Defaults to the Simmate version 
    (e.g. "0.7.0").
    """

    s3task: S3Task = None
    """
    The supervised-staged-shell task (or S3Task) that this workflow uses to run.
    For understanding what the calculation does and the settings it uses, users
    should start here. You can also use a workflows `s3task.run` to run the workflow
    without storing results in the database.
    """

    database_table: Calculation = None
    """
    The database table where calculation information (such as the prefect_flow_run_id)
    is stored. The table should use `simmate.database.base_data_types.Calculation`
    
    In many cases, this table will contain all of the results you need. However,
    pay special attention to NestedWorkflows, where your results are often tied
    to a final task.
    """

    description_doc_short: str = None
    """
    A quick description for this workflow. This will be shown in the website UI
    in the list-view of all different workflow presets.
    """

    @classmethod
    def run_config(
        cls,
        structure: Structure,
        command: str = None,
        source: dict = None,
        directory: str = None,
        copy_previous_directory: bool = False,
        pre_sanitize_structure: bool = None,
        pre_standardize_structure: bool = None,
    ):
        """
        The workflow method, which can be overwritten when inheriting from this
        class. This can be either a staticmethod or classmethod.

        #### The default run method

        There is a default run method implemented that is for S3Tasks.

        Builds a workflow from a S3Task and it's corresponding database table.

        Very often with Simmate's S3Tasks, the workflow for a single S3Task is
        the same. The workflow is typically made of three tasks:

        1. loading the input parameters and registering the calculation
        2. running the calculation (what this S3Task does on its own)
        3. saving the calculation results

        Task 1 and 3 always use the same functions, where we just need to tell
        it which database table we are registering/saving to.

        Because of this common recipe for workflows, we use this method to make
        the workflow for us.
        """
        # local import to prevent circular import error
        from simmate.workflow_engine.common_tasks import (
            load_input_and_register,
            save_result,
        )

        # make sure the workflow is configured properly first
        if not cls.s3task:
            raise NotImplementedError(
                "Please either set the s3task attribute or write a custom run method!"
            )

        parameters_cleaned = load_input_and_register(
            structure=structure,
            command=command,
            source=source,
            directory=directory,
            copy_previous_directory=copy_previous_directory,
            pre_sanitize_structure=pre_sanitize_structure,
            pre_standardize_structure=pre_standardize_structure,
        ).result()

        result = cls.s3task.run(**parameters_cleaned).result()

        save_result(result)

        return result

    @classmethod
    @cache
    def to_prefect_flow(cls) -> Flow:
        """
        Converts this workflow into a Prefect flow
        """

        # Instead of the @flow decorator, we build the flow instance directly
        flow = Flow(
            fn=cls.run_config,
            name=cls.name_full,
            version=cls.version,
            # Skip type checking because I don't have robust typing yet
            # e.g. Structure type inputs also accept inputs like a filename
            validate_parameters=False,
        )

        # as an extra, we set this attribute to the prefect flow instance, which
        # allows us to access the source Simmate Workflow easily with Prefect's
        # context managers.
        flow.simmate_workflow = cls

        return flow

    @classmethod
    def run(cls, **kwargs) -> State:
        """
        A convience method to run a workflow as a subflow in a prefect context.
        """
        subflow = cls.to_prefect_flow()
        state = subflow(**kwargs)

        # We don't want to block and wait because this might disable parallel
        # features of subflows. We therefore return the state and let the
        # user decide if/when to block.
        # result = state.result()

        return state

    @classmethod
    @property
    def name_full(cls) -> str:
        """
        Standardized name of the workflow. This converts the class name like so:
        `Static_Energy__VASP__Matproj` --> `static-energy.vasp.matproj`
        """
        if not len(cls.__name__.split("__")) == 3:
            raise Exception("Make sure you are following Simmate naming conventions!")

        # convert to dot format
        name = cls.__name__.replace("__", ".")

        # adds a hyphen between each capital letter
        # copied from https://stackoverflow.com/questions/199059/
        name = re.sub(r"(\w)([A-Z])", r"\1-\2", name)

        return name.lower()

    @classmethod
    @property
    def name_project(cls) -> str:
        """
        Name of the Project this workflow is associated with. This is the first
        portion of the flow name (e.g. "static-energy")
        """
        return cls.name_full.split(".")[0]

    @classmethod
    @property
    def name_calculator(cls) -> str:
        """
        Name of the calculator this workflow is associated with. This is the second
        portion of the flow name (e.g. "vasp")
        """
        return cls.name_full.split(".")[1]

    @classmethod
    @property
    def name_preset(cls) -> str:
        """
        Name of the settings/preset this workflow is associated with. This is the third
        portion of the flow name (e.g. "matproj" or "matproj-prebader")
        """
        return cls.name_full.split(".")[2]

    # BUG: naming this `description` causes issues.
    # See https://github.com/PrefectHQ/prefect/issues/3911
    @classmethod
    @property
    def description_doc(cls) -> str:
        """
        This simply returns the documentation string of this workflow -- so this
        is the same as `__doc__`. This attribute is only defined for beginners
        to python and for use in django templates for the website interface.
        """
        return cls.__doc__ or cls.s3task.__doc__  # NEEDS REFACTOR

    @classmethod
    @property
    def parameter_names(cls) -> List[str]:
        """
        Gives a list of all the parameter names for this workflow.
        """
        # Iterate through and grab the parameters for the run method. We also
        # sort them alphabetically for consistent results.
        parameter_names = list(cls.to_prefect_flow().parameters.properties.keys())
        parameter_names.sort()
        return parameter_names

    @classmethod
    @property
    def parameter_names_required(cls) -> List[str]:
        """
        Gives a list of all the required parameter names for this workflow.
        """
        return cls.to_prefect_flow().parameters.required

    @classmethod
    def show_parameters(cls):
        """
        Prints a list of all the parameter names for this workflow.
        """
        # use yaml to make the printout pretty (no quotes and separate lines)
        print(yaml.dump(cls.parameter_names))

    @classmethod
    @property
    def parameters_to_register(cls) -> List[str]:
        """
        (experimental feature)
        A list of input parameters that should be used to register the calculation.
        """
        parameters_to_register = [
            "prefect_flow_run_id"
        ]  # run is always used to register but is never an input parameter

        table_columns = cls.database_table.get_column_names()

        for parameter in cls.parameter_names:
            if parameter in table_columns:
                parameters_to_register.append(parameter)

        # check special cases where input parameter doesn't match to a column name
        if "structure_string" in table_columns:
            parameters_to_register.append("structure")

        # put in alphabetical order for consistent results
        parameters_to_register.sort()

        return parameters_to_register

    @classmethod
    def _register_calculation(cls, **kwargs) -> Calculation:
        """
        If the workflow is linked to a calculation table in the Simmate database,
        this adds the flow run to the database.

        Parameters passed should be deserialized and cleaned.

        This method should not be called directly as it is used within the
        `run_cloud` method and `load_input_and_register` task.
        """

        # We first need to grab the database table where we want to register
        # the calculation run to. We can grab the table from either...
        #   1. the database_table attribute
        #   2. flow_context --> flow_name --> flow --> then grab its database_table

        # If this method is being called on the base Workflow class, that
        # means we are trying to register a calculation from within a flow
        # context -- where the context has information such as the workflow
        # we are using (and the database table linked to that workflow).
        if cls == Workflow:

            run_context = FlowRunContext.get()
            workflow = run_context.flow.simmate_workflow
            database_table = workflow.database_table

            # as an extra, add the prefect_flow_run_id the kwargs in case it
            # wasn't set already.
            if "prefect_flow_run_id" not in kwargs:
                kwargs["prefect_flow_run_id"] = str(run_context.flow_run.id)

        # Otherwise we should be using the subclass Workflow that has the
        # database_table property set.
        else:
            workflow = cls  # we have the workflow class already
            database_table = cls.database_table

        # Registration is only possible if a table is provided. Some
        # special-case workflows don't store calculation information bc the flow
        # is just a quick python analysis.
        if not database_table:
            print("No database table found. Skipping registration.")
            return

        # grab the registration kwargs from the parameters provided and then
        # convert them to a python object format for the database method
        register_kwargs = {
            key: kwargs.get(key, None) for key in workflow.parameters_to_register
        }
        register_kwargs_cleaned = cls._deserialize_parameters(**register_kwargs)

        # SPECIAL CASE: for customized workflows we need to convert the inputs
        # back to json before saving to the database.
        if "workflow_base" in register_kwargs_cleaned:
            parameters_serialized = cls._serialize_parameters(**register_kwargs_cleaned)
            prefect_flow_run_id = parameters_serialized.pop("prefect_flow_run_id", None)
            calculation = database_table.from_prefect_id(
                prefect_flow_run_id=prefect_flow_run_id,
                **parameters_serialized,
            )
        else:
            # load/create the calculation for this workflow run
            calculation = database_table.from_prefect_id(**register_kwargs_cleaned)

        return calculation

    @staticmethod
    def _serialize_parameters(**parameters) -> dict:
        """
        Converts input parameters to json-sealiziable objects that Prefect can
        use.

        This method should not be called directly as it is used within the
        run_cloud() method.
        """

        # TODO: consider moving this into prefect's core code as a contribution.
        # This alternatively might be a pydantic contribution

        # Because many flows allow object-type inputs (such as structure object),
        # we need to serialize these inputs before scheduling them with prefect
        # cloud. To do this, I only check for two potential methods:
        #     as_dict
        #     to_dict
        # These were chosen based on common pymatgen methods, but I may change
        # this in the future. As another alternative, I could also cloudpickle
        # input objects when they are not JSON serializable.
        # OPTIMIZE: Prefect current tries to JSON serialize within their
        # client.create_flow_run method. In the future, we may want to move
        # this functionality there.

        parameters_serialized = {}
        for parameter_key, parameter_value in parameters.items():

            try:
                json.dumps(parameter_value)
            except TypeError:
                if hasattr(parameter_value, "as_dict"):
                    parameter_value = parameter_value.as_dict()
                elif hasattr(parameter_value, "to_dict"):
                    parameter_value = parameter_value.to_dict()

                # workflow_base and input_parameters are special cases that
                # may require a refactor (for customized workflows)
                elif parameter_key == "workflow_base":
                    parameter_value = parameter_value.name
                elif parameter_key == "input_parameters":
                    # recursive call to this function
                    parameter_value = Workflow._serialize_parameters(**parameter_value)

                else:
                    parameter_value = cloudpickle.dumps(parameter_value)
            parameters_serialized[parameter_key] = parameter_value
        return parameters_serialized

    @staticmethod
    def _deserialize_parameters(**parameters) -> dict:
        """
        converts all parameters to appropriate python objects
        """

        from simmate.toolkit import Structure
        from simmate.toolkit.diffusion import MigrationHop, MigrationImages

        parameters_cleaned = parameters.copy()

        #######
        # SPECIAL CASE: customized workflows have their parameters stored under
        # "input_parameters" instead of the base dict
        # THIS INVOLVES A RECURSIVE CALL TO THIS SAME METHOD
        if "workflow_base" in parameters.keys():
            # This is a non-modular import that can cause issues and slower
            # run times. We therefore import lazily.
            from simmate.workflows.utilities import get_workflow

            parameters_cleaned["workflow_base"] = get_workflow(
                parameters["workflow_base"]
            )
            parameters_cleaned["input_parameters"] = Workflow._deserialize_parameters(
                **parameters["input_parameters"]
            )
            return parameters_cleaned
        #######

        # we don't want to pass arguments like command=None or structure=None if the
        # user didn't provide this input parameter. Instead, we want the workflow to
        # use its own default value. To do this, we first check if the parameter
        # is set in our kwargs dictionary and making sure the value is NOT None.
        # If it is None, then we remove it from our final list of kwargs. This
        # is only done for command, directory, and structure inputs -- as these
        # are the three that are typically assumed to be present (see the CLI).
        parameter_to_filter = [
            "command",
            "directory",
            "pre_sanitize_structure",
            "pre_standardize_structure",
        ]
        for parameter in parameter_to_filter:
            if not parameters.get(parameter, None):
                parameters_cleaned.pop(parameter, None)

        # The remaining checks look to intialize input to toolkit objects

        structure = parameters.get("structure", None)
        if structure:
            parameters_cleaned["structure"] = Structure.from_dynamic(structure)
        else:
            parameters_cleaned.pop("structure", None)

        if "structures" in parameters.keys():
            structure_filenames = parameters["structures"].split(";")
            parameters_cleaned["structures"] = [
                Structure.from_dynamic(file) for file in structure_filenames
            ]

        if "migration_hop" in parameters.keys():
            migration_hop = MigrationHop.from_dynamic(parameters["migration_hop"])
            parameters_cleaned["migration_hop"] = migration_hop

        if "migration_images" in parameters.keys():
            migration_images = MigrationImages.from_dynamic(
                parameters["migration_images"]
            )
            parameters_cleaned["migration_images"] = migration_images

        if "supercell_start" in parameters.keys():
            parameters_cleaned["supercell_start"] = Structure.from_dynamic(
                parameters["supercell_start"]
            )

        if "supercell_end" in parameters.keys():
            parameters_cleaned["supercell_end"] = Structure.from_dynamic(
                parameters["supercell_end"]
            )

        return parameters_cleaned

    # -------------------------------------------------------------------------
    #
    # All methods beyond this point require a Prefect server to be running
    # and Simmate to be connected to it.
    #
    # -------------------------------------------------------------------------

    @classmethod
    @property
    @cache
    @async_to_sync
    async def deployment_id(cls) -> str:
        """
        Grabs the deployment id from the prefect database if it exists, and
        if not, creates the depolyment
        """

        async with get_client() as client:
            response = await client.read_deployments(
                flow_filter=FlowFilter(
                    name={"any_": [cls.name_full]},
                ),
            )

        # If this is the first time accessing the deployment id, we will need
        # to create the deployment
        if not response:
            deployment_id = cls._create_deployment()
            return deployment_id

        # there should only be one deployment associated with this workflow
        # if it's been deployed already.
        elif len(response) == 1:
            return str(response[0].id)

        else:
            raise Exception("There are duplicate deployments for this workflow!")

    @classmethod
    @async_to_sync
    async def _create_deployment(cls) -> str:
        """
        Registers this workflow to the prefect database as a deployment.

        This method should not be called directly. It will be called by
        other methods when appropriate
        """

        # CREATE_DEPLOYMENT method is not yet updated in 2.0b8
        #
        # async with get_client() as client:
        #     response = await client.create_deployment(
        #         name="leonardo-deployment",
        #         flow_location="./leo_flow.py",
        #         tags=['tutorial','test'],
        #         parameters={'name':'Leo'},
        #     )

        # For now, this is a modification of the create_deployment code
        # until they fix the method.

        from prefect.deployments import Deployment

        deployment = Deployment(
            flow=cls.to_prefect_flow(),
            name=cls.name_full,
            packager=OrionPackager(serializer=PickleSerializer()),
            tags=[
                "simmate",
                cls.name_project,
                cls.name_calculator,
            ],
        )
        # OPTIMIZE: it would be better if I could figure out the ImportSerializer
        # here. Only issue is that prefect would need to know to import AND
        # call a method.

        async with get_client() as client:
            deployment_id = await deployment.create()

        return str(deployment_id)  # convert from UUID to str first

    @classmethod
    @async_to_sync
    async def _submit_to_prefect(cls, **kwargs) -> str:
        """
        Submits a flow run to prefect cloud.

        This method should not be used directly. Instead use `run_cloud`.
        """

        # The reason we have this code as a separate method is because we want
        # to isolate Prefect's async calls from Django's sync-restricted calls
        # (i.e. django raises errors if called within an async context).
        # Therefore, methods like `run_cloud` can't have both this async code
        # AND methods like _register_calculation that make sync database calls.

        async with get_client() as client:
            response = await client.create_flow_run_from_deployment(
                deployment_id=cls.deployment_id,
                **kwargs,
            )

        flow_run_id = str(response.id)
        return flow_run_id

    @classmethod
    def run_cloud(cls, **kwargs) -> str:
        """
        This schedules the workflow to run remotely on Prefect Cloud.

        #### Parameters

        - `labels`:
            a list of labels to schedule the workflow with

        - `wait_for_run`:
            whether to wait for the workflow to finish. If False, the workflow
            will simply be submitted and then exit. The default is True.

        - `**kwargs`:
            all options that are normally passed to the workflow.run() method

        #### Returns

        - The flow run id that was used in prefect cloud.


        #### Usage

        Make sure you have Prefect properly configured and have registered your
        workflow with the backend.

        Note that this method can be viewed as a fork of:
            - from prefect.tasks.prefect.flow_run import create_flow_run
        It can also be viewed as a more convenient way to call to client.create_flow_run.
        I don't accept any other client.create_flow_run() inputs besides 'labels'.
        This may change in the future if I need to set flow run names or schedules.
        """

        # Prefect does not properly deserialize objects that have
        # as as_dict or to_dict method, so we use a custom method to do that here
        parameters_serialized = cls._serialize_parameters(**kwargs)
        # BUG: What if we are submitting using a filename? We don't want to
        # submit to a cluster and have the job fail because it doesn't have
        # access to the file. One solution could be to deserialize right before
        # serializing in the next line in order to ensure parameters that
        # accept file names are submitted with all necessary data.

        # Now we submit the workflow.
        flow_run_id = cls._submit_to_prefect(parameters=parameters_serialized)

        # Because we often want to save some info to our database even before
        # the calculation starts/finishes, we do that here. An example is
        # storing the structure and prefect id that we just submitted.
        cls._register_calculation(prefect_flow_run_id=flow_run_id, **kwargs)
        # BUG: Will there be a race condition here? What if the workflow finishes
        # and tries writing to the databse before this is done?
        # BUG: if parameters are improperly set, this line will fail, while the
        # job submission (above) will suceed. Should I cancel the flow run if
        # this occurs?

        # return the flow_run_id for the user
        return flow_run_id

    @classmethod
    @property
    @async_to_sync
    async def nflows_submitted(cls) -> int:
        """
        Queries Prefect to see how many workflows are in a scheduled, running,
        or pending state.
        """

        async with get_client() as client:
            response = await client.read_flow_runs(
                flow_filter=FlowFilter(
                    name={"any_": [cls.name_full]},
                ),
                flow_run_filter=FlowRunFilter(
                    state={"type": {"any_": ["SCHEDULED", "PENDING", "RUNNING"]}}
                ),
            )

        return len(response)
