import os
import shutil
import subprocess
import time

import heroku3

from celery.task import task


class ChaBotException(Exception):
    pass


def set_heroku_config(application_name, key, value):
    api_key = os.environ.get('HEROKU_API_KEY')
    if not api_key:
        raise ChaBotException('No Heroku API key')
    conn = heroku3.from_key(api_key)

    # Try at most 5 times to do this
    for _ in range(5):
        if conn.apps().get(application_name):
            app = conn.apps()[application_name]
            app.config()[key] = value  # this actually saves itself when you set it!
            return True
        time.sleep(5)
    return False


def get_heroku_config(application_name, key):
    api_key = os.environ.get('HEROKU_API_KEY')
    if not api_key:
        raise ChaBotException('No Heroku API key')
    conn = heroku3.from_key(api_key)

    # Try at most 5 times to do this
    for _ in range(5):
        if conn.apps().get(application_name):
            app = conn.apps()[application_name]
            return app.config()[key]
        time.sleep(5)
    return False


def docker_up():
    return subprocess.run(['docker-compose', '-f', 'docker-compose.compute_worker.yml', 'up', '-d', '--build'])


def check_return_code(cmd, error_message):
    if cmd.returncode != 0:
        raise ChaBotException(error_message)


@task
def pr_opened(payload):
    pr_number = payload['pull_request']['number']
    app_name = f'competitions-v2-staging-pr-{pr_number}'

    # Set the API URL to be passed to the compute worker
    success = set_heroku_config(app_name, 'SUBMISSIONS_API_URL', f'https://{app_name}.herokuapp.com/api')
    if not success:
        raise ChaBotException(f'Unable to set SUBMISSIONS_API_URL for {app_name}')

    # Get pr servers queue url
    queue = get_heroku_config(app_name, 'CLOUDAMQP_URL')
    if not queue:
        raise ChaBotException('Unable to get information from heroku, or variable does not exist')

    repo_clone_url = payload['repository']['clone_url']
    branch_name = payload['pull_request']['head']['ref']
    branch_path = os.path.join('repos', branch_name)
    if os.path.exists(branch_path):
        raise ChaBotException('A compute worker for a branch with this name already exists')

    saved_cwd = os.getcwd()
    os.mkdir(branch_path)
    os.chdir(branch_path)
    git_clone = subprocess.run(['git', 'clone', '--single-branch', '--branch', branch_name, repo_clone_url, '.'])
    check_return_code(git_clone, f'git clone returned a non-zero code for branch {branch_name}')
    with open('.env', 'w+') as f:
        f.write(f'BROKER_URL={queue}')

    cp = subprocess.run(['cp', os.path.join(saved_cwd, 'docker-compose.compute_worker.yml'), '.'])
    check_return_code(cp, f'could not copy docker-compose.compute_worker.yml file into branch {branch_name}')

    docker = docker_up()
    check_return_code(docker, f'docker-compose up -d for branch {branch_name} returned non-zero code')

    os.chdir(saved_cwd)


def pr_merged(payload):
    saved_cwd = os.getcwd()
    branch_path = os.path.join('repos', 'develop')
    pull = True
    if not os.path.exists(branch_path):
        pull = False
        os.mkdir(branch_path)
    os.chdir(branch_path)
    if pull:
        git = subprocess.run(['git', 'pull'])
        check_return_code(git, 'git pull on branch develop returned non-zero code')
        docker = docker_up()
        check_return_code(docker, 'docker-compose up -d on develop returned a non-zero code')
    else:
        app_name = f'competitions-v2-staging'

        # Set the API URL to be passed to the compute worker
        success = set_heroku_config(app_name, 'SUBMISSIONS_API_URL', f'https://{app_name}.herokuapp.com/api')
        if not success:
            raise ChaBotException(f'Unable to set SUBMISSIONS_API_URL for {app_name}')

        # Get pr servers queue url
        queue = get_heroku_config(app_name, 'CLOUDAMQP_URL')
        if not queue:
            raise ChaBotException('Unable to get information from heroku, or variable does not exist')

        repo_clone_url = payload['repository']['clone_url']
        git = subprocess.run(['git', 'clone', repo_clone_url, '.'])
        check_return_code(git, 'git clone for branch develop returned non-zero code')
        with open('.env', 'w+') as f:
            f.write(f'BROKER_URL={queue}')

        cp = subprocess.run(['cp', os.path.join(saved_cwd, 'docker-compose.compute_worker.yml'), '.'])
        check_return_code(cp, f'could not copy docker-compose.compute_worker.yml file into develop')

        docker = docker_up()
        check_return_code(docker, 'docker-compose up -d on develop returned non-zero code')
    os.chdir(saved_cwd)


@task
def pr_closed(payload):
    saved_cwd = os.getcwd()
    branch_name = payload['pull_request']['head']['ref']
    branch_path = os.path.join('repos', branch_name)
    if not os.path.exists(branch_path):
        raise ChaBotException(f'{branch_path} does not exist. cannot remove container')
    os.chdir(branch_path)
    docker_down = subprocess.run(['docker-compose', '-f', 'docker-compose.compute_worker.yml', 'down'])
    check_return_code(docker_down, f'docker-compose down for branch {branch_name} returned a non-zero code')
    os.chdir(saved_cwd)
    shutil.rmtree(branch_path)
    if payload.get('pull_request', {}).get('merged'):
        if payload.get('pull_request', {}).get('base', {}).get('ref') == 'develop':
            pr_merged(payload)


@task
def pr_updated(payload):
    saved_cwd = os.getcwd()
    branch_name = payload['pull_request']['head']['ref']
    branch_path = os.path.join('repos/', branch_name)
    if not os.path.exists(branch_path):
        return pr_opened(payload)
    os.chdir(branch_path)
    git = subprocess.run(['git', 'pull'])
    check_return_code(git, f'git pull for {branch_name} returned non-zero code')
    docker = docker_up()
    check_return_code(docker, f'docker-compose up -d for branch {branch_name} returned non-zero code')
    os.chdir(saved_cwd)
