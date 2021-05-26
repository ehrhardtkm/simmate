# -*- coding: utf-8 -*-

from django.db import models

from simmate.database.base import Structure


class OcdStructure(Structure):

    """ Base Info """

    # OQMD ID
    # For now, max length of 14 is overkill: 'oqmd-123456789'
    id = models.CharField(max_length=14, primary_key=True)

    # Extra data by OCD
    # See my notes in the scraping file. There's more metadata to add but I leave
    # this out for now.

    """ Properties """

    # OPTIMIZE: is it better to just set the attribute than to have a fixed
    # property that's defined via a function?
    source = "OCD"

    @property
    def external_link(self):
        # Links to the AFLOW dashboard for this structure. An example is...
        #   http://aflow.org/material/?id=aflow:ffea9279661c929f
        # !!! I could also consider an alternative link which points to an interactive
        # REST endpoint. The API is also sporatic for these, An example one is...
        #   aflowlib.duke.edu/AFLOWDATA/ICSD_WEB/FCC/Dy1Mn2_ICSD_602151
        id_formatted = self.id.replace("-",":")
        return f"http://aflow.org/material/?id={id_formatted}"
