import os
import mimetypes
import requests


class GithubAPI(object):

    BASE_URL = 'https://api.github.com'
    CONFIG = os.path.join(os.path.dirname(__file__), 'config')

    def __init__(self):
        self.headers = {
                'Accept': 'application/vnd.github.manifold-preview',
        }
        with open(self.CONFIG, 'r') as f:
            for line in f:
                if line.startswith('GITHUB_TOKEN='):
                    key, value = line.split('=', 1)
                    self.headers['Authorization'] = 'token %s' % value.strip()

    def get(self, path):
        url = self.BASE_URL + path
        return requests.get(url, headers=self.headers)

    def post(self, path, **kwargs):
        url = self.BASE_URL + path
        return requests.post(url, headers=self.headers, **kwargs)

    def patch(self, path, **kwargs):
        url = self.BASE_URL + path
        return requests.patch(url, headers=self.headers, **kwargs)

    def delete(self, path, **kwargs):
        url = self.BASE_URL + path
        return requests.delete(url, headers=self.headers, **kwargs)

    def upload_headers(self, filename):
        mimetype = mimetypes.guess_type(filename)[0]
        headers = ['%s: %s' % (k, v) for k, v in self.headers.items()]
        headers.append('Content-Type: %s' % mimetype)
        return headers
