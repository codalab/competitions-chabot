import hmac
import os
from hashlib import sha1


from flask import Flask, request, Response
from flask.cli import load_dotenv

import utils

app = Flask(__name__)


@app.route('/')
def say_hello():
    return Response("Hi. I'm the ChaBot. I spin up compute workers for codalab PRs!", status=200)


@app.route('/pull_request', methods=('POST',))
def pull_request():
    # Verify message secret
    received_sig = request.headers['X-Hub-Signature'].split('=', 1)[1]
    computed_sig = hmac.new(bytearray(os.environ.get('SPECIAL_SECRET'), 'utf-8'), request.data, sha1).hexdigest()
    if received_sig != computed_sig:
        return Response(response='Forbidden: signatures do not match', status=403)

    # Message verified, proceed
    action_functions = {
        'opened': utils.pr_opened,
        'reopened': utils.pr_opened,
        'closed': utils.pr_closed,
        'merged': utils.pr_closed,
    }

    payload = request.json
    action = payload['action']

    if action not in action_functions:
        return Response(status=403)

    action_functions[action](payload)

    return Response(response='Success', status=200)


if __name__ == '__main__':
    load_dotenv()
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', False)
    FLASK_PORT = os.environ.get('FLASK_PORT', 8000)
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT)
