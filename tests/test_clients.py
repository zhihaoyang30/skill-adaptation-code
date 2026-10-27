import io
import json
from unittest.mock import patch

import pytest

from models import chat


@pytest.mark.parametrize('fmt', ['openai', 'anthropic'])
def test_api_payload_and_credential_location(fmt, monkeypatch):
    monkeypatch.setenv('TEST_API_KEY', 'local-test-token')
    spec = {'api_format':fmt, 'model':'example', 'api_key_env':'TEST_API_KEY', 'base_url':'https://example.com/v1', 'parameters':{}}
    response = {'choices':[{'message':{'content':'ok'}}]} if fmt == 'openai' else {'content':[{'type':'text','text':'ok'}]}
    def open_request(request, timeout):
        payload = json.loads(request.data)
        assert payload['model'] == 'example'
        assert 'local-test-token' not in request.data.decode()
        assert request.get_header('Authorization' if fmt == 'openai' else 'X-api-key')
        assert request.full_url.endswith('/chat/completions' if fmt == 'openai' else '/messages')
        return io.BytesIO(json.dumps(response).encode())
    with patch('urllib.request.urlopen', side_effect=open_request):
        assert chat(spec, 'system', 'user') == 'ok'
