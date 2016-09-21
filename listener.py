import SimpleHTTPServer
import SocketServer
import json
import logging
import cgi
import os

import sys
import tempfile

import time
from openalpr import Alpr

from slacker import Slacker, Error


alpr = Alpr("eu", "/srv/openalpr/config/openalpr.conf.defaults", "/srv/openalpr/runtime_data")
alpr.set_top_n(1)
alpr.set_default_region("md")

logger = logging.getLogger('openalpr')
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)

logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = 0

slack = Slacker(os.environ['SLACK_TOKEN'])


def load_license_plates(licenseplate_file='/data/licenseplates.json'):
    if not os.path.isfile(licenseplate_file):
        refresh_license_plates(licenseplate_file=licenseplate_file)
    with open(licenseplate_file, 'rt') as f_lp:
        license_plates = json.load(f_lp)
    return license_plates


def refresh_license_plates(licenseplate_file='/data/licenseplates.json'):
    if not os.path.isfile(licenseplate_file) or \
                            time.time() - os.path.getmtime(licenseplate_file) > (24 * 60 * 60):
        users_list = slack.users.list().body['members']

        license_plates = {}
        for user in users_list:
            try:
                if ('is_bot' in user and user['is_bot']) or ('deleted' in user and user['deleted']) or \
                                'profile' not in user or 'email' not in user['profile']:
                    continue
                profile = slack.users.profile.get(user['id'])
                if profile is None or 'profile' not in profile.body:
                    continue
                profile = profile.body['profile']
                if 'fields' in profile and profile['fields'] is not None and \
                                'Xf2E30E95Y' in profile['fields']:
                    license_plate = profile['fields']['Xf2E30E95Y']['value'].replace('-', '')
                    license_plates[license_plate] = user['name']
            except (TypeError, Error):
                continue
        with open(licenseplate_file, 'wt') as f_lp:
            json.dump(license_plates, f_lp)


class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        logging.error(self.headers)
        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST'})

        saved_fns = ""

        try:
            logger.info('Received fields: {}'.format(','.join([f for f in form])))
            f = form['file']
            logger.info('Received file successfully')
            img_file = tempfile.mkstemp(suffix='.jpg')
            with open(img_file[1], 'wb') as f_img:
                f_img.write(f.file.read())
            res = alpr.recognize_file(img_file[1])
            logger.info('License plate recognition result: {}'.format(res['results']))
            self.send_response(200)
            self.end_headers()
            if len(res['results']) > 0:
                self.wfile.write(res['results'][0])
                license_plate = res['results'][0]['plate'].replace('-', '')
                license_plates = load_license_plates()
                if license_plate in license_plates:
                    logger.info("{}'s car is approaching - opening the gate!".format(license_plates[license_plate]))
                    slack.chat.post_message('@augubot1', '%auguvalet open')
                    slack.chat.post_message('#auguvalet', '@{} is parking his car.'
                                            .format(license_plates[license_plate]))
            refresh_license_plates()
            return True, "File(s) '%s' upload success!" % saved_fns
        except (IOError, KeyError) as e:
            logger.error(e.message)
            self.send_response(200)
            self.end_headers()
            refresh_license_plates()
            return False, "Can't create file to write, do you have permission to write?"


if __name__ == '__main__':
    port = sys.argv[1]

    Handler = ServerHandler

    httpd = SocketServer.TCPServer(("", int(port)), Handler)

    logger.info("serving at port {}".format(port))
    httpd.serve_forever()
