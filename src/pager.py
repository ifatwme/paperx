import fitz
import os


class Pager:
    def __init__(self, base_dir, in_filename, image_format) -> None:
        self._base_dir = os.environ.get("BASE_DIR", base_dir)
        self._in_filename = in_filename
        self._image_format = image_format
        self._file_path = os.path.join(self._base_dir, self._in_filename)
        self.open_file()

    def open_file(self):
        self._doc = fitz.open(self._file_path)

    def paginator(self):
        for i, page in enumerate(self._doc.pages()):
            out_filename = self._in_filename.split(".")[:-1]
            pix = page.get_pixmap()
            image_path = os.path.join(self._base_dir, out_filename)
            pix.save(image_path, output=self._image_format)
