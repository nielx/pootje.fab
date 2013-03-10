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
