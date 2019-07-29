import os
import shutil
import subprocess
import time

import heroku3


def set_heroku_config(application_name, key, value):
    conn = heroku3.from_key(os.environ.get('HEROKU_API_KEY'))

    # Try at most 5 times to do this
    for _ in range(5):
        if conn.apps().get(application_name):
            app = conn.apps()[application_name]
            app.config()[key] = value  # this actually saves itself when you set it!
            return True
        time.sleep(5)
    return False


def get_heroku_config(application_name, key):
    conn = heroku3.from_key(os.environ.get('HEROKU_API_KEY'))

    # Try at most 5 times to do this
    for _ in range(5):
        if conn.apps().get(application_name):
            app = conn.apps()[application_name]
            return app.config()[key]
        time.sleep(5)
    return False


def pr_opened(payload):
    pr_number = payload['pull_request']['number']
    app_name = f'competitions-v2-staging-pr-{pr_number}'

    # Set the API URL to be passed to the compute worker
    set_heroku_config(app_name, 'SUBMISSION_API_URL', f'https://{app_name}.herokuapp.com/api')

    # Get pr servers queue url
    queue = get_heroku_config(app_name, 'CLOUDAMQP_URL')

    repo_clone_url = payload['repository']['clone_url']
    branch_name = payload['pull_request']['head']['ref']
    branch_path = os.path.join('repos', branch_name)
    if os.path.exists(branch_path):
        print('some kind of error')  # Todo: deal with this
        return 'path already exists'

    saved_cwd = os.getcwd()
    os.mkdir(branch_path)
    os.chdir(branch_path)
    subprocess.run(['git', 'clone', '--single-branch', '--branch', branch_name, repo_clone_url, '.'])
    with open('.env', 'w+') as f:
        f.write(f'BROKER_URL={queue}')
    subprocess.run(['docker-compose', '-f', 'docker-compose.compute_worker.yml', 'up', '-d'])
    os.chdir(saved_cwd)


def pr_closed(payload):
    saved_cwd = os.getcwd()
    branch_name = payload['pull_request']['head']['ref']
    branch_path = os.path.join('repos', branch_name)
    os.chdir(branch_path)
    subprocess.run(['docker-compose', '-f', 'docker-compose.compute_worker.yml', 'down'])
    os.chdir(saved_cwd)
    shutil.rmtree(branch_path)
