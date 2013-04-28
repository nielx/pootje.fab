Automation for deployment of Pootle on vmdev.haiku-os.org
=========================================================

This repository contains the management tools to install and maintain Haiku's
Pootle installation.

Bootstrapping a new installation
--------------------------------

Bootstrapping is the creation of an entry into /srv and includes:
 * Fetching the code
 * Setting up a virtual Python environment
 * Installing all Pootle dependencies
 
To get from bootstrapping to running, use:
 * fab <staging/production> bootstrap
 * fab <staging/production> deploy

Scripts
-------

The scripts that are used by Pootle and written for its migration are copied
to the scripts directory in the project dir. Note that the cron-script will
not be set up automatically: there is no sense in doing that. The cron script
is added to the distribution for future (re)construction.
