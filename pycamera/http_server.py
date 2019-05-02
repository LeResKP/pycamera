#!/usr/bin/env python

import argparse
import cv2
import time

from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread

boundary = '--boundarydonotcross'


JPG_RESPONSE_HEADERS = [
    ('Connection', 'close'),
    ('Content-Type', 'image/jpg'),
]

MJPG_RESPONSE_HEADERS = [
    ('Connection', 'close'),
    ('Content-Type', 'image/jpg'),
    ('Pragma', 'no-cache'),
    ('Cache-Control', 'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0'),
    ('Content-Type', 'multipart/x-mixed-replace;boundary=%s' % boundary)
]


class VideoStream(Thread):

    def __init__(self):
        super(VideoStream, self).__init__()
        self.video_stream = cv2.VideoCapture(0)
        self.frame = None
        self._active = True

    def stop(self):
        self._active = False
        self.video_stream.release()

    def run(self):
        while self._active:
            grabbed, frame = self.video_stream.read()
            if not grabbed:
                continue
            self.frame = frame
            time.sleep(0.1)


stream = VideoStream()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class HttpHandler(SimpleHTTPRequestHandler):

    def _get_frame(self):
        return stream.frame

    def _get_jpg(self):
        frame = self._get_frame()
        ret, jpeg = cv2.imencode(
            '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return jpeg.tobytes()

    def _screenshot(self):
        self.send_response(200)
        for k, v in JPG_RESPONSE_HEADERS:
            self.send_header(k, v)
        img = self._get_jpg()
        self.send_header('Content-length', str(len(img)))
        self.end_headers()
        self.wfile.write(img)

    def _stream(self):
        self.send_response(200)
        for k, v in MJPG_RESPONSE_HEADERS:
            self.send_header(k, v)

        while True:
            content = self._get_jpg()
            self.end_headers()
            self.wfile.write(bytes(boundary, 'UTF-8'))
            self.end_headers()
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            time.sleep(0.1)

    def do_GET(self):
        if self.path == '/screenshot':
            return self._screenshot()

        if self.path == '/stream':
            return self._stream()

        self.send_response(404)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--host', default='localhost', help='Server hostname')
    parser.add_argument('--port', default=8080, type=int, help='Server port')
    args = parser.parse_args()
    stream.start()
    server = ThreadedHTTPServer((args.host, args.port), HttpHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        stream.stop()


if __name__ == '__main__':
    main()
