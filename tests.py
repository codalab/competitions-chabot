import hmac
import json
import os
from hashlib import sha1
from unittest import mock, TestCase

from flask.cli import load_dotenv

from app import flask_app


class ChaBotTests(TestCase):
    def setUp(self):
        load_dotenv()
        self.SECRET = os.environ.get('SPECIAL_SECRET')
        self.client = flask_app.test_client()

    @staticmethod
    def build_payload(action):
        return {
            'action': action
        }

    def mock_utils(self, payload, signature=None):
        body = bytearray(json.dumps(payload), 'utf-8')
        signature = signature or hmac.new(bytearray(self.SECRET, 'utf-8'), body, sha1).hexdigest()
        with mock.patch('app.utils.pr_opened') as mock_pr_opened:
            with mock.patch('app.utils.pr_closed') as mock_pr_closed:
                response = self.client.post('/pull_request', headers={'X-Hub-Signature': f'sha1={signature}'}, json=payload)
                return response, mock_pr_opened, mock_pr_closed

    def test_say_hello(self):
        resp = self.client.get('/')
        assert resp.status_code == 200
        assert resp.data == b"Hi. I'm the ChaBot. I spin up compute workers for codalab PRs!"

    def test_verifying_github_signature(self):
        payload = self.build_payload('opened')
        resp, mock_open, mock_close = self.mock_utils(payload, signature='asdfasdf')
        assert resp.status_code == 403
        assert not mock_open.called
        assert not mock_close.called

    def test_pr_opened(self):
        payload = self.build_payload('opened')
        resp, mock_open, mock_close = self.mock_utils(payload)
        assert resp.status_code == 200
        assert mock_open.called
        assert not mock_close.called

    def test_pr_reopened(self):
        payload = self.build_payload('reopened')
        resp, mock_open, mock_close = self.mock_utils(payload)
        assert resp.status_code == 200
        assert mock_open.called
        assert not mock_close.called

    def test_pr_closed(self):
        payload = self.build_payload('closed')
        resp, mock_open, mock_close = self.mock_utils(payload)
        assert resp.status_code == 200
        assert not mock_open.called
        assert mock_close.called

    def test_pr_merged(self):
        payload = self.build_payload('merged')
        resp, mock_open, mock_close = self.mock_utils(payload)
        assert resp.status_code == 200
        assert not mock_open.called
        assert mock_close.called

