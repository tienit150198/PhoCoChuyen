"""Feedback attachments: durable, bounded raster files with owner/operator access."""
import base64
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, PngImagePlugin

from game import accounts, feedback_images, player_feedback as pfb
from game.storage import Store
from tests import test_player_feedback as feedback_fixture

REG = feedback_fixture.REG


def image_url(fmt='PNG', size=(16, 12), raw=None, **save):
    if raw is None:
        stream = io.BytesIO()
        Image.new('RGB', size, '#709acc').save(stream, fmt, **save)
        raw = stream.getvalue()
    mime = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp', 'GIF': 'image/gif'}[fmt]
    return 'data:' + mime + ';base64,' + base64.b64encode(raw).decode('ascii')


class ImageDecoderResourceTests(unittest.TestCase):
    def test_concurrent_decode_is_refused_without_waiting(self):
        entered, release = threading.Event(), threading.Event()
        def decode(value):
            if threading.current_thread() is holder:
                entered.set()
                release.wait(5)
            return {'data': b'pixels'}
        holder = threading.Thread(target=lambda: feedback_images.decode_images(['one']))
        with patch.object(feedback_images, '_decode', side_effect=decode):
            holder.start()
            self.assertTrue(entered.wait(2))
            try:
                with self.assertRaises(feedback_images.ImageUploadError) as exc:
                    feedback_images.decode_images(['two'])
                self.assertEqual(exc.exception.status, 503)
                self.assertEqual(feedback_images.decode_images([]), [])
            finally:
                release.set()
                holder.join(2)
        self.assertEqual(len(feedback_images.decode_images([image_url()])), 1)

    def test_invalid_image_releases_the_decode_slot(self):
        with self.assertRaises(feedback_images.ImageUploadError):
            feedback_images.decode_images(['invalid'])
        self.assertEqual(len(feedback_images.decode_images([image_url()])), 1)

    def test_busy_response_preserves_service_status_without_a_database_write(self):
        with feedback_images._DECODE_GATE:
            with self.assertRaises(pfb.FeedbackError) as exc:
                pfb.submit(None, 'unused-token', {}, dict(kind='bug', text='Báo lỗi có ảnh', images=[image_url()]))
        self.assertEqual((exc.exception.code, exc.exception.status), ('image_busy', 503))

    def test_png_reencoding_strips_text_and_appended_payload(self):
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('private', 'private details')
        raw = base64.b64decode(image_url(pnginfo=metadata).split(',')[1]) + b'<script>trailing</script>'
        result = feedback_images.decode_images([image_url(raw=raw)])[0]
        self.assertNotIn(b'private details', result['data'])
        self.assertNotIn(b'<script>', result['data'])

    def test_decoded_budget_rejects_over_twelve_point_six_megapixels(self):
        with self.assertRaises(feedback_images.ImageUploadError):
            feedback_images.decode_images([image_url(size=(4200, 3001))])

    def test_exif_orientation_keeps_pixels_but_not_private_metadata(self):
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = 'private location'
        result = feedback_images.decode_images([image_url('JPEG', exif=exif)])[0]
        with Image.open(io.BytesIO(result['data'])) as image:
            self.assertEqual(image.size, (12, 16))
            self.assertFalse(image.getexif())
        self.assertNotIn(b'private location', result['data'])


class FeedbackImageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'feedback-images'
        self.store = Store(self.path)
        self.token, _, _ = self.store.session()

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def send(self, images, token=None):
        token = token or self.token
        return pfb.submit(self.store, token, self.store.read(token)[0],
                          dict(kind='bug', text='Ảnh màn hình của lỗi', images=images))

    def test_three_images_have_small_metadata_in_owner_and_admin_lists(self):
        self.send([image_url(fmt) for fmt in ('PNG', 'JPEG', 'WEBP')])
        mine = pfb.list_mine(self.store, self.token)
        images = mine[0].get('images', [])
        self.assertEqual(len(images), 3)
        self.assertEqual(pfb.list_admin(self.store)['items'][0]['images'], images)
        for item in images:
            self.assertEqual(set(item), {'id', 'url', 'mime', 'width', 'height', 'size'})
            self.assertTrue(item['url'].startswith('/api/feedback/images/'))
            self.assertEqual((item['width'], item['height']), (16, 12))
        self.assertNotIn('base64', json.dumps(mine))

    def test_invalid_uploads_are_rejected_before_feedback_is_inserted(self):
        good = image_url()
        invalid = [None, {}, 'not-a-list', [good] * 4, [None], [{}], ['data:image/png;base64,%%%'],
                   ['https://example.com/photo.png'], [image_url(raw=b'<script>alert(1)</script>')],
                   [good.replace('image/png', 'image/jpeg')], [good, 'broken'], [image_url('GIF')],
                   [image_url(raw=b'x' * (2 * 1024 * 1024 + 1))],
                   [image_url(size=(5000, 5000))], [image_url(raw=b'\x89PNG\r\n\x1a\n')]]
        for value in invalid:
            with self.subTest(value=str(value)[:60]), self.assertRaises(pfb.FeedbackError) as exc:
                self.send(value)
            self.assertEqual(exc.exception.status, 400)
        self.assertEqual(pfb.list_mine(self.store, self.token), [])

    def test_exact_byte_limit_is_accepted_and_discarded_trailing_bytes_are_not_stored(self):
        raw = base64.b64decode(image_url().split(',')[1])
        self.send([image_url(raw=raw + b'\0' * (2 * 1024 * 1024 - len(raw)))])
        images = pfb.list_mine(self.store, self.token)[0]['images']
        self.assertEqual(len(images), 1)
        self.assertLess(images[0]['size'], 1024)

    def test_animated_and_truncated_images_are_rejected(self):
        stream = io.BytesIO()
        Image.new('RGB', (20, 20), 'red').save(stream, 'PNG', save_all=True,
            append_images=[Image.new('RGB', (20, 20), 'blue')], duration=100, loop=0)
        for raw in (stream.getvalue(), base64.b64decode(image_url().split(',')[1])[:-12]):
            with self.assertRaises(pfb.FeedbackError):
                self.send([image_url(raw=raw)])

    def test_bytes_are_reencoded_without_metadata_or_appended_payload(self):
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('private', 'hidden metadata')
        url = image_url(pnginfo=metadata)
        raw = base64.b64decode(url.split(',')[1]) + b'<script>trailing payload</script>'
        self.send([image_url(raw=raw)])
        item = pfb.list_mine(self.store, self.token)[0].get('images', [])
        self.assertEqual(len(item), 1)
        binary, mime = pfb.read_image(self.store, self.token, item[0]['id'])
        self.assertEqual(mime, 'image/png')
        self.assertNotIn(b'hidden metadata', binary)
        self.assertNotIn(b'<script>', binary)
        with Image.open(io.BytesIO(binary)) as photo:
            photo.load()
            self.assertEqual(photo.size, (16, 12))

    def test_images_survive_edit_reply_done_prune_and_another_store(self):
        fid = self.send([image_url()])['id']
        before = pfb.list_mine(self.store, self.token)[0].get('images', [])
        self.assertEqual(len(before), 1)
        self.assertEqual(pfb.edit(self.store, self.token, dict(id=fid, text='Nội dung sửa lại'))['item']['images'], before)
        self.assertEqual(pfb.update(self.store, fid, status='done', reply='Đã sửa lỗi')['images'], before)
        with self.store.connect() as db:
            db.execute('UPDATE player_feedback SET created_at=1,updated_at=1,replied_at=1 WHERE id=?', (fid,))
        self.assertEqual(pfb.prune(self.store, days=1), 0)
        self.store.close_pool()
        self.store = Store(self.path)
        self.assertEqual(pfb.list_mine(self.store, self.token)[0]['images'], before)
        self.assertTrue(pfb.read_image(self.store, self.token, before[0]['id'])[0])
        self.assertEqual(pfb.forget(self.store, self.token), 1)
        with self.assertRaises(pfb.FeedbackError) as exc:
            pfb.read_image(self.store, self.token, before[0]['id'])
        self.assertEqual(exc.exception.status, 404)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM player_feedback_images').fetchone()[0], 0)

    def test_image_access_follows_owner_account_and_revokes_admin_access(self):
        self.send([image_url()])
        images = pfb.list_mine(self.store, self.token)[0].get('images', [])
        self.assertEqual(len(images), 1)
        iid = images[0]['id']
        other, _, _ = self.store.session()
        for token in (None, other):
            with self.assertRaises(pfb.FeedbackError):
                pfb.read_image(self.store, token, iid)
        signed = accounts.register(self.store, self.token, dict(REG, username='image_owner'))['token']
        signed2 = accounts.login(self.store, other, dict(username='image_owner', password=REG['password']))['token']
        self.assertEqual(pfb.read_image(self.store, signed, iid), pfb.read_image(self.store, signed2, iid))
        admin_token, _, _ = self.store.session()
        admin = accounts.register(self.store, admin_token, dict(REG, username='image_admin'))['token']
        with patch.dict(os.environ, {'ADMIN_USERS': 'image_admin'}):
            self.assertTrue(pfb.read_image(self.store, admin, iid)[0])
        with patch.dict(os.environ, {'ADMIN_USERS': ''}), self.assertRaises(pfb.FeedbackError) as exc:
            pfb.read_image(self.store, admin, iid)
        self.assertEqual(exc.exception.status, 404)

    def test_idle_guest_cleanup_keeps_submitted_feedback_and_images(self):
        self.send([image_url()])
        before = pfb.list_admin(self.store)['items'][0]['images']
        sid = self.store.key(self.token)
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET updated_at='2000-01-01 00:00:00' WHERE sid=?", (sid,))
        self.store.prune(idle_days=1)
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT sid FROM sessions WHERE sid=?', (sid,)).fetchone())
        self.assertEqual(pfb.list_admin(self.store)['items'][0]['images'], before)


class FeedbackImageHTTPTests(unittest.TestCase):
    setUpClass = classmethod(feedback_fixture.FeedbackHTTPTests.setUpClass.__func__)
    tearDownClass = classmethod(feedback_fixture.FeedbackHTTPTests.tearDownClass.__func__)
    setUp = feedback_fixture.FeedbackHTTPTests.setUp
    req = feedback_fixture.FeedbackHTTPTests.req
    device = feedback_fixture.FeedbackHTTPTests.device
    signed = feedback_fixture.FeedbackHTTPTests.signed
    admin = feedback_fixture.FeedbackHTTPTests.admin

    def raw_get(self, dev, path):
        import http.client
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request('GET', path, headers={'Cookie': dev.get('cookie', '')})
        response = con.getresponse()
        out = response.status, response.read(), dict(response.getheaders())
        con.close()
        return out

    def test_upload_over_old_64k_limit_and_protected_binary_reads(self):
        dev, stranger = self.device(), self.device()
        raw = io.BytesIO()
        Image.frombytes('RGB', (256, 256), os.urandom(256 * 256 * 3)).save(raw, 'PNG')
        body = dict(kind='bug', text='Lỗi có ba ảnh kèm theo', images=[image_url(raw=raw.getvalue())] * 3)
        self.assertGreater(len(json.dumps(body)), 64 * 1024)
        status, sent = self.req(dev, '/api/feedback', 'POST', body)
        self.assertEqual(status, 200, sent)
        images = self.req(dev, '/api/feedback/mine')[1]['items'][0].get('images', [])
        self.assertEqual(len(images), 3)
        url = images[0]['url']
        status, data, headers = self.raw_get(dev, url)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'image/png')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(headers['Cache-Control'], 'private, no-store')
        self.assertEqual(headers['Cross-Origin-Resource-Policy'], 'same-origin')
        self.assertEqual(Image.open(io.BytesIO(data)).size, (256, 256))
        self.assertEqual(self.raw_get(stranger, url)[0], 404)
        self.assertEqual(self.raw_get({}, url)[0], 401)
        self.assertEqual(self.raw_get(self.admin(), url)[0], 200)
        self.assertEqual(self.raw_get(dev, '/api/feedback/images/invalid')[0], 404)
        self.assertEqual(self.req(dev, '/api/feedback/edit', 'POST', dict(id=sent['id'], text='Sửa góp ý', padding='x'*65536))[0], 413)

    def test_image_requests_still_enforce_csrf_json_and_count(self):
        dev = self.device()
        body = dict(kind='bug', text='Báo lỗi có ảnh', images=[image_url()])
        self.assertEqual(self.req(dev, '/api/feedback', 'POST', body, csrf=False)[0], 403)
        self.assertEqual(self.req(dev, '/api/feedback', 'POST', body, headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.req(dev, '/api/feedback', 'POST', dict(body, images=body['images']*4))[0], 400)
        self.assertEqual(self.req(dev, '/api/feedback', 'POST', dict(body, images=['data:image/png;base64,!!!']))[0], 400)
        self.assertEqual(self.req(dev, '/api/feedback', 'POST', dict(body, images=[image_url(raw=b'x'*(2*1024*1024+1))]))[0], 400)
        self.assertEqual(self.req(dev, '/api/feedback/mine')[1]['items'], [])

    def test_upload_body_ceiling_is_checked_before_reading(self):
        import http.client
        from game.feedback_images import MAX_BODY
        dev = self.device()
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        try:
            con.request('POST', '/api/feedback', headers={'Cookie': dev['cookie'],
                'X-Game-CSRF': dev['csrf'], 'Content-Type': 'application/json', 'Content-Length': str(MAX_BODY + 1)})
            response = con.getresponse()
            self.assertEqual(response.status, 413)
            self.assertIn('error', json.loads(response.read()))
        finally:
            con.close()


if __name__ == '__main__':
    unittest.main()
