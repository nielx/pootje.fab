#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2012 Zuza Software Foundation
#
# NOTE: this file is heavily modified fabfile from Pootle for use on Haiku 
# servers
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from fabric.api import env, sudo, put, run, task
from fabric.colors import red
from fabric.context_managers import cd, prefix
from fabric.contrib.console import confirm
from fabric.contrib.files import exists, upload_template
from fabric.operations import require
import os
import time

#
# Settings
#
env.hosts = ['vmdev.haiku-os.org']
env.python = '/usr/bin/python2.7'
env.pootle_repository = 'https://github.com/translate/pootle.git'

# 
# Set up the environment
#
@task
def staging():
    """Work on the staging environment"""
    env.environment = 'staging'
    env.project_path = "/srv/pootle-staging"
    env.apache_server_name = "i18n-next.haiku-os.org"


@task
def production():
    """Work on the staging environment"""
    env.environment = 'production'
    env.project_path = "/srv/pootle-production"
    env.apache_server_name = "i18n.haiku-os.org"

#
# Main tasks
#
@task
def bootstrap(git_tag=None):
    """Set up a fresh instance ready to be further deployed and activated"""
    require('environment', provided_by=[staging, production])
    if (exists('%(project_path)s' % env)):
        print ('The staging environment already exists at %(project_path)s. Please clean it up manually and try again.'
            % env)
        return

    # Set up directory
    sudo('mkdir %(project_path)s' % env)
    
    # Set up python virtual env
    sudo('virtualenv -p %(python)s --no-site-packages %(project_path)s/env'
            % env)
    with prefix('source %(project_path)s/env/bin/activate' % env):
        sudo('easy_install pip' % env)
    
    # Download source
    sudo('git clone %(pootle_repository)s %(project_path)s/app' % env)
        
    # Create the log dir
    sudo('mkdir %(project_path)s/logs' % env)
    sudo('chown wwwrun:www %(project_path)s/logs' % env)
    
    # Create the catalogs dir
    sudo('mkdir %(project_path)s/catalogs' % env)
    sudo('chown wwwrun:www %(project_path)s/catalogs' % env)
    
    # Create the scripts dir
    sudo('mkdir %(project_path)s/scripts' % env)
    
    print("The environment is prepared.")


@task
def deploy(git_tag):
    """Updates the code and installs the configuration for apache"""
    require('environment', provided_by=[staging, production])

    try:
        put('requirements/' + git_tag, "/tmp/requirements.txt")
    except:
        print(red("There is no support for this version of Pootle. Please provide a requirements file"))
        return

    print('Deploying the site...')
    
    # Update the code
    with cd(os.path.join(env.project_path, 'app')):
        sudo('git fetch origin')
        sudo('git checkout '+ git_tag)
    
    # Fetch/update all packages
    with prefix('source %(project_path)s/env/bin/activate' % env):
        sudo('pip install -r %(project_path)s/app/requirements/deploy.txt' 
                % env)
        sudo('pip install -r /tmp/requirements.txt')

    # Update the configuration files
    enable_environment()
    
    sudo('cp /srv/pootle-settings/91-local-secrets-%(environment)s.conf %(project_path)s/app/pootle/settings/' % env)
    
    # Configure WSGI application
    upload_template('pootle.wsgi', env.project_path, context=env, use_sudo=True)
    
    # Configure and install settings
    upload_template('settings.conf' % env,
                    os.path.join(env.project_path, 'app', 'pootle', 
                    'settings', '90-local.conf'),
                    use_sudo=True, context=env)
    
    # Deploy static resources
    deploy_static()
    
    # Set up the scripts
    scripts = ['scripts/fingerprint.py', 'scripts/finish_output_catalogs.py',
              'scripts/import_language_catkeys.py',
              'scripts/import_templates_from_haiku-files.py']
    
    for script in scripts:
        put(script, "%(project_path)s/scripts/" % env, use_sudo=True)
    upload_template('cron-script/update_translations', 
                    '/etc/cron-scripts/update_translations_%(environment)s' % env,
                    context=env, use_sudo=True)

    # setup/update the database
    #with cd('%(project_path)s/app' % env):
    #    with prefix('source %(project_path)s/env/bin/activate' % env):
    #        sudo('python manage.py setup')
    print("Deployment done. Run database modifications/scripts manually.")

@task
def deploy_static():
    """Runs `collectstatic` to collect all the static files"""
    require('environment', provided_by=[staging, production])

    print('Collecting and building static files...')

    with cd('%(project_path)s/app' % env):
        with prefix('source %(project_path)s/env/bin/activate' % env):
            sudo('mkdir -p pootle/assets')
            sudo('python manage.py collectstatic --noinput --clear')
            sudo('python manage.py assets build')

@task
def backup():
    """Make a backup of the project dir and the database in the home dir"""
    require('environment', provided_by=[staging, production])
    
    if not exists('~/.pgpass'):
        print("In order to make a backup you will need to put the password to the database in a .pgpass file")
        print("See: http://www.postgresql.org/docs/current/static/libpq-pgpass.html")
        print("You will need it for the pootle account")
        return
    
    print('Synchronizing the catalogs to disk')
    
    with cd('%(project_path)s/app' % env):
        with prefix('source %(project_path)s/env/bin/activate' % env):
            sudo('python manage.py sync_stores', user='wwwrun')

    with cd('%(project_path)s/catalogs' % env):
        sudo('chmod -R a+r .')
    
    
    timestring = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    
    with cd('~'):
        run("tar -cvjf pootle_%s_files_%s.tar.bz2 %s" % \
            (env["environment"], timestring, env["project_path"]))
        run("pg_dump -U pootle pootle_%s | bzip2 > pootle_%s_database_%s.bz2" % \
            (env["environment"], env["environment"], timestring))
    
    print("Done")
    
@task
def copy_data_to_staging():
    """Copy the production data to the staging environment"""
    
    if not exists('~/.pgpass'):
        print("In order to perform these operations, you will need to store the password of the database in a .pgpass file")
        print("See: http://www.postgresql.org/docs/current/static/libpq-pgpass.html")
        print("You will need it for the pootle and the baron account")
        return
    
    confirm("This will destroy all data of the staging environment. Do you want to continue?", default=False)

    print(red("Deleting current data in staging"))
    run("dropdb -U pootle pootle_staging", warn_only=True)
    sudo("rm -rf /srv/pootle_staging/catalogs/*", user="wwwrun")
    
    print(red("Now copying data from production"))
    run("createdb -U postgres -O pootle pootle_staging")
    run("pg_dump -U pootle pootle_production | psql -U pootle pootle_staging")
    with cd('/srv/pootle-production/app' % env):
        with prefix('source /srv/pootle-production/env/bin/activate' % env):
            sudo('python manage.py sync_stores', user='wwwrun')
    sudo("cp -R /srv/pootle-production/catalogs/* /srv/pootle-staging/catalogs/", user='wwwrun')

@task
def disable_environment(destination_domain):
    """Disable an environment and redirect to a URL"""
    require('environment', provided_by=[staging, production])
    
    env.destination_domain = destination_domain
    
    # Update the configuration files
    upload_template('virtualhost-disabled.conf', 
            '/etc/apache2/vhosts.d/i18n-%s.haiku-os.org.conf' % (env.environment,),
            context=env, use_sudo=True)
    
    sudo('/sbin/service apache2 reload')

@task
def enable_environment():
    """Enable an environment"""
    require('environment', provided_by=[staging, production])
    
    # Update the configuration files
    upload_template('virtualhost.conf', 
            '/etc/apache2/vhosts.d/i18n-%s.haiku-os.org.conf' % (env.environment,),
            context=env, use_sudo=True)
    
    sudo('/sbin/service apache2 reload')
    
