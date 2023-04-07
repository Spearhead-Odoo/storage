# Copyright 2023 ACSONE SA/NV (http://acsone.eu).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import os
import shutil
import tempfile

from odoo.tests.common import HttpCase


class TestFsAttachmentInternalUrl(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.backend = cls.env.ref("fs_storage.default_fs_storage")
        temp_dir = tempfile.mkdtemp()
        cls.temp_backend = cls.env["fs.storage"].create(
            {
                "name": "Temp FS Storage",
                "protocol": "file",
                "code": "tmp_dir",
                "directory_path": temp_dir,
            }
        )
        cls.temp_dir = temp_dir
        cls.gc_file_model = cls.env["fs.file.gc"]
        cls.content = b"This is a test attachment"
        cls.attachment = (
            cls.env["ir.attachment"]
            .with_context(
                storage_location=cls.temp_backend.code,
                storage_file_path="test.txt",
            )
            .create({"name": "test.txt", "raw": cls.content})
        )

        @cls.addClassCleanup
        def cleanup_tempdir():
            shutil.rmtree(temp_dir)

    def tearDown(self) -> None:
        super().tearDown()
        # empty the temp dir
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))

    def assertDownload(
        self, url, headers, assert_status_code, assert_headers, assert_content=None
    ):
        res = self.url_open(url, headers=headers)
        res.raise_for_status()
        self.assertEqual(res.status_code, assert_status_code)
        for header_name, header_value in assert_headers.items():
            self.assertEqual(
                res.headers.get(header_name),
                header_value,
                f"Wrong value for header {header_name}",
            )
        if assert_content:
            self.assertEqual(res.content, assert_content, "Wong content")
        return res

    def test_fs_attachment_internal_url(self):
        self.authenticate("admin", "admin")
        self.assertDownload(
            self.attachment.internal_url,
            headers={},
            assert_status_code=200,
            assert_headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Disposition": "inline; filename=test.txt",
            },
            assert_content=self.content,
        )
