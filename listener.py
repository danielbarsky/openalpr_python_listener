import SimpleHTTPServer
import SocketServer
import logging
import cgi

import sys
import tempfile

from openalpr import Alpr

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

        logger.info(form)

        try:
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
            return True, "File(s) '%s' upload success!" % saved_fns
        except (IOError, KeyError) as e:
            logger.error(e.message)
            self.send_response(200)
            self.end_headers()
            return False, "Can't create file to write, do you have permission to write?"


if __name__ == '__main__':
    port = sys.argv[1]

    Handler = ServerHandler

    httpd = SocketServer.TCPServer(("", int(port)), Handler)

    logger.info("serving at port {}".format(port))
    httpd.serve_forever()
