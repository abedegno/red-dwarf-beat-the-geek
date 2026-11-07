from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from tools.owner.preview import RangeHandler


class PreviewTests(unittest.TestCase):
    def test_byte_ranges_and_missing_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "clip.mp4").write_bytes(b"0123456789")
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), partial(RangeHandler, directory=tmp)
            )
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urlopen(
                    Request(base + "/clip.mp4", headers={"Range": "bytes=2-5"})
                ) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.read(), b"2345")
                    self.assertEqual(response.headers["Content-Range"], "bytes 2-5/10")
                    self.assertEqual(response.headers["Content-Type"], "video/mp4")
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + "/missing.mp4")
                self.assertEqual(error.exception.code, 404)
                error.exception.close()
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + "/clip.mp4", headers={"Range": "bytes=99-"}))
                self.assertEqual(error.exception.code, 416)
                error.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
