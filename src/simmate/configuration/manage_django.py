# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------------------

import os
import shutil
import sys
import django

# --------------------------------------------------------------------------------------

# NOTE -- connecting just the Django database ORM has only a 0.05 second advantage
# on the initial import and then only 1.8e-7 second advantage after. Based on
# that, there really isn't much to gain from running the reduced setup. Even
# in ETL methods, I believe the bottleneck will still be the internet connection
# and not the django_setup. Having users always setup all of django can solve
# a lot of potential headaches at roughly the same speed.


def setup_django_full():  # Wall time: 250 ms first call and 780 ns after   

    # see if django has already been configured. If so, just exit this function.
    if "DJANGO_SETTINGS_MODULE" in os.environ:
        return

    # The code below is the equiv of running 'python manage.py shell'
    # This sets up all of django for its full use. You can being importing
    # models after this is setup.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simmate.website.core.settings")
    django.setup()


def connect_db():  # Wall time: 200 ms first call and 600 ns after

    # see if django has already been configured. If so, just exit this function.
    # Note that this check is different than the one used in setup_django_full.
    from django.conf import settings
    if settings.configured:
        return

    # import the settings I want from the actual django settings file
    from simmate.website.core.settings import BASE_DIR, DATABASES, DEBUG

    # For speed, I only want this app installed
    # I also need to write out the full import path from django here.
    INSTALLED_APPS = ("simmate.website.diffusion.apps.DiffusionConfig",)
    # set these values

    settings.configure(
        BASE_DIR=BASE_DIR,
        DEBUG=DEBUG,
        DATABASES=DATABASES,
        INSTALLED_APPS=INSTALLED_APPS,
    )
    django.setup()


def setup_django_cli():  # TODO -- move this to the command_line module
    # This is if you call the file directory from the command line interface (cli)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simmate.website.core.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


# --------------------------------------------------------------------------------------


def reset_db(apps_to_migrate=["diffusion", "execution"]):
    # Apps to init.
    # !!! In the future, I should do a more robust search, rather than hardcode here.
    # !!! maybe just grab all folders in the base directory via os.listdir()?

    # grab base directory and the location of the database file
    from simmate.website.core.settings import BASE_DIR, DATABASES

    db_filename = DATABASES["default"]["NAME"]

    # delete the sqlite3 database file if it exists
    if os.path.exists(db_filename):
        os.remove(db_filename)

    # go through each listed directory in the base directory
    # and delete all folders named 'migrations'
    for app in apps_to_migrate:
        migration_dir = os.path.join(BASE_DIR, app, "migrations")
        if os.path.exists(migration_dir):
            shutil.rmtree(migration_dir)

    # setup django before we call any commands
    setup_django_full()

    # execute the following commands to build the database
    from django.core.management import call_command
    call_command("makemigrations", *apps_to_migrate)
    call_command("migrate")

# --------------------------------------------------------------------------------------


if __name__ == "simmate.configuration.manage_django":
    # This is a little hacking that I do to speed up when I setup django and
    # not redoing it again. When I import this module, it just automatically
    # runs this function. Otherwise I would have to make sure I'm connected
    # to the django database and have django settings properly configured. In
    # every single module I import models. That would mean I need two lines:
    #   from simmate.configuration.manage_django import setup_django_full
    #   setup_django_full() # ensures setup
    # Then I would import Models after these two lines. With this hack, I instead
    # only need to have one line before I import any other models:
    #   from simmate.configuration import manage_django # ensures setup
    # Not only that, but it's faster too! The first import takes 250 ms and then
    # after that it takes 370 ns. 996
    setup_django_full()

# TODO -- move this to the commandline module
# if __name__ == "__main__":
#     setup_django_cli()
