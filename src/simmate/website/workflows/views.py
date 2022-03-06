# -*- coding: utf-8 -*-

from django import forms
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from prefect.backend.flow_run import FlowView

from simmate.workflows.utilities import (
    # WORKFLOW_TYPES,
    get_workflow,
    get_list_of_workflows_by_type,
)
from simmate.website.workflows.forms import MITRelaxationForm, StructureForm
from simmate.workflow_engine import WorkflowTask


@login_required
def workflows_all(request):

    # TODO: maybe instead load these descriptions from the simmate.{module}'s docstr
    # This would look something like...
    # all_metadata = {}
    # for flow_type in WORKFLOW_TYPES:
    #     --> grab the module
    #     --> use the __doc__ as the text.

    workflows_metadata = {
        "static-energy": (
            "These workflows calculate the energy for a structure. In many cases, "
            "this also involves calculating the lattice strain and forces for each site."
        ),
        "relaxation": (
            "These workflows geometry-optimize a structure's the lattice and sites "
            "until specified covergence criteria are met."
        ),
        "population-analysis": (
            "These workflows evaluate where electrons exist in a structure -- and "
            "they are often assigned to a specific site/atom. As a result of assigning "
            "electrons, these workflows give predicted oxidation states for each site."
        ),
        "band-structure": (
            "These workflows calculate the electronic band structure for a material."
        ),
        "density-of-states": (
            "These workflows calculate the electronic density of states for a material."
        ),
        "dynamics": (
            "These workflows run a molecular dynamics simulation for a material. This "
            "often involves iteratively evaluating the energy/forces of structure at "
            "specific temperature (or temperature ramp)."
        ),
        "diffusion": (
            "These workflows evaluate the diffusion of an atom through a material. "
            "At this time, these workflows are entirely Nudged-Elastic-Band (NEB) "
            "calculations."
        ),
    }

    # now let's put the data and template together to send the user
    context = {
        "active_tab_id": "workflows",
        "workflows_metadata": workflows_metadata,
    }
    template = "workflows/all.html"
    return render(request, template, context)


@login_required
def workflows_by_type(request, workflow_type):

    workflow_names = get_list_of_workflows_by_type(workflow_type)

    # pull the information together for each individual flow
    workflows = [get_workflow(n) for n in workflow_names]

    # now let's put the data and template together to send the user
    context = {
        "active_tab_id": "workflows",
        "workflow_type": workflow_type,
        "workflows": workflows,
    }
    template = "workflows/by_type.html"
    return render(request, template, context)


@login_required
def workflow_detail(request, workflow_type, workflow_name):
    # note, workflow_name here is the workflow.name_short

    workflow_name_full = workflow_type + "/" + workflow_name
    workflow = get_workflow(workflow_name_full)

    # In order to make links to the monitoring pages for each of these, we need
    # to grab the prefect id
    # If no flow exists in Prefect cloud, a ValueError is raised, so I can't
    # share this info
    try:
        flow_id = FlowView.from_flow_name(workflow_name_full).flow_id
        nflows_submitted = workflow.nflows_submitted
    except:  # ValueError is no query result. Need to test what error is if no API key.
        flow_id = None
        nflows_submitted = None

    # TODO: grab some metadata about this calc. For example...
    # ncalculations = MITRelaxation.objects.count()

    # ----- Dynamically make a form from this model -----

    # TODO: consider using workflow.result_table.__base__ (or __bases__) to
    # determine which form mix-ins to use. Or alternatively use inspect.getrmo
    # to get all subclasses (as DatabaseTable.from_toolkit does)
    class ResultsForm(forms.ModelForm, StructureForm):
        class Meta:
            model = workflow.result_table
            fields = "__all__"
            # To remove fields, we combine the exclude attributes from
            # each subclass.
            exclude = StructureForm.Meta.exclude

    # ---- Querying results ----
    if request.method == "POST":
        search_form = ResultsForm(request.POST, request.FILES)
        if search_form.is_valid():
            # TODO
            raise Exception("This view is still under development")
    else:
        # create an empty form
        search_form = ResultsForm()

        # even though our form is empty, we still want
        # Grab the most recent 50 calculations that have been registered/ran
        calculations = workflow.result_table.objects.order_by("-created_at").all()[:50]

        # We also want to count how many total calculations there are beyond these
        # most recent 50.
        ncalculations_possible = workflow.result_table.objects.count()

    # --------------------------

    # now let's put the data and template together to send the user
    context = {
        "active_tab_id": "workflows",
        "workflow": workflow,
        "flow_id": flow_id,
        "search_form": search_form,
        "calculations": calculations,
        "ncalculations_possible": ncalculations_possible,
        "nflows_submitted": nflows_submitted,
    }
    template = "workflows/detail.html"
    return render(request, template, context)


@login_required
def workflow_submit(request, workflow_type, workflow_name):

    workflow_name_full = workflow_type + "/" + workflow_name
    workflow = get_workflow(workflow_name_full)

    if request.method == "POST":
        submission_form = MITRelaxationForm(request.POST, request.FILES)
        if submission_form.is_valid():
            # grab the structure (as a pymatgen object) and all other inputs
            structure = submission_form.cleaned_data["structure_file"]
            labels = submission_form.cleaned_data["labels"]
            vasp_command = submission_form.cleaned_data["vasp_command"]

            # We can now submit the workflow for the structure.
            flow_run_id = workflow.run_cloud(
                structure=structure,
                vasp_command=vasp_command,
                labels=labels,
                wait_for_run=False,
            )

            return redirect(f"https://cloud.prefect.io/simmate/flow-run/{flow_run_id}")
    else:
        submission_form = MITRelaxationForm()

    # now let's put the data and template together to send the user
    context = {
        "active_tab_id": "workflows",
        "workflow": workflow,
        "submission_form": submission_form,
    }
    template = "workflows/submit.html"
    return render(request, template, context)


@login_required
def workflow_run_detail(request, workflow_type, workflow_name, workflow_run_id):

    workflow_name_full = workflow_type + "/" + workflow_name
    workflow = get_workflow(workflow_name_full)
    workflow_run = workflow.result_table.get(id=workflow_run_id)

    # !!! this is old code that may be useful as I reimpliment detail views
    # Make the convergence figure and convert it to an html div
    # figure_convergence = calculation.get_convergence_plot()
    # figure_convergence_html = figure_convergence.to_html(
    #     full_html=False, include_plotlyjs=False
    # )

    # now let's put the data and template together to send the user
    context = {
        "active_tab_id": "workflows",
        "workflow_run": workflow_run,
        # "figure_convergence_html": figure_convergence_html,
    }
    template = "workflows/detail_run.html"
    return render(request, template, context)
