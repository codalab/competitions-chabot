import hmac
import os
from hashlib import sha1

from flask import Flask, request, Response
from flask.cli import load_dotenv
from tasks import pr_updated, pr_opened, pr_closed
from celery_config import make_celery

flask_app = Flask(__name__)
celery_app = make_celery(flask_app)


def log_info(message):
    flask_app.logger.info(message)


@flask_app.route('/')
def say_hello():
    return Response("Hi. I'm the ChaBot. I spin up compute workers for codalab PRs!", status=200)


@flask_app.route('/pull_request', methods=('POST',))
def pull_request():
    secret = os.environ.get('SPECIAL_SECRET')
    if not secret:
        log_info('Missing SPECIAL_SECRET environment variable')
        return Response(response='Server Error: missing environment variables', status=500)
    # Verify message secret
    received_sig = request.headers['X-Hub-Signature'].split('=', 1)[1]
    computed_sig = hmac.new(bytearray(os.environ.get('SPECIAL_SECRET'), 'utf-8'), request.data, sha1).hexdigest()
    if received_sig != computed_sig:
        log_info("Received a request with mismatched signatures")
        return Response(response='Forbidden: signatures do not match', status=403)
    # Message verified, proceed
    action_functions = {
        'opened': pr_opened,
        'reopened': pr_opened,
        'closed': pr_closed,
        'merged': pr_closed,
        'synchronize': pr_updated,
    }

    payload = request.json
    action = payload.get('action')
    if action not in action_functions or action is None:
        log_info(f'Unsupported action: {action or "None"}')
        return Response(response='Forbidden', status=403)
    action_functions[action].apply_async((payload,))
    return Response(response='Success', status=200)
