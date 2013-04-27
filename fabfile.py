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

from fabric.api import env, sudo, put, task
from fabric.context_managers import cd, prefix
from fabric.contrib.files import exists, upload_template
from fabric.operations import require
import os

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


@task
def production():
    """Work on the staging environment"""
    env.environment = 'production'
    env.project_path = "/srv/pootle-production"

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
    
    # Check out the git tag
    if git_tag:
        with cd(os.path.join(env.project_path, 'app')):
            sudo('git checkout '+ git_tag)    

    # Fetch/update all packages
    with prefix('source %(project_path)s/env/bin/activate' % env):
        sudo('pip install -r %(project_path)s/app/requirements/deploy.txt' 
                % env)
        # Future versions might change, but the current version of Pootle
        # does not install the psycopg2 package needed for PostgreSQL
        # connections
        sudo('pip install -U psycopg2')
    
    # Create the log dir
    sudo('mkdir %(project_path)s/logs' % env)
    sudo('chown wwwrun:www %(project_path)s/logs' % env)
    
    print("The environment is prepared.")


@task
def deploy(git_tag=None):
    """Updates the code and installs the configuration for apache"""
    require('environment', provided_by=[staging])

    print('Deploying the site...')
    
    # Update the code
    with cd(os.path.join(env.project_path, 'app')):
        sudo('git fetch')   
        if not git_tag:
            git_tag = "HEAD"
        sudo('git checkout '+ git_tag)
    
    # Update the configuration files
    put('virtualhost.conf', 
            '/etc/apache2/vhosts.d/i18n-%s.haiku-os.org.conf' % (env.environment,),
            use_sudo=True)
    
    sudo('cp /srv/pootle-settings/91-local-secrets-%(environment)s.conf %(project_path)s/app/pootle/settings/' % env)
    
    # Configure WSGI application
    upload_template('pootle.wsgi', env.project_path, context=env, use_sudo=True)
    
    # Configure and install settings
    upload_template('settings-%(environment)s.conf' % env,
                    os.path.join(env.project_path, 'app', 'pootle', 
                    'settings', '90-local.conf'),
                    use_sudo=True, context=env)
    
    # Deploy static resources
    deploy_static()
    
    # install_site()

@task
def deploy_static():
    """Runs `collectstatic` to collect all the static files"""
    require('environment', provided_by=[staging])

    print('Collecting and building static files...')

    with cd('%(project_path)s/app' % env):
        with prefix('source %(project_path)s/env/bin/activate' % env):
            sudo('mkdir -p pootle/assets')
            sudo('python manage.py collectstatic --noinput --clear')
            sudo('python manage.py assets build')
