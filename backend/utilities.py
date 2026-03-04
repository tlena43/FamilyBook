from pdf2image import convert_from_path
from PIL import Image
import os

def makeCachedUpload(app, filename):
    cFilepath = os.path.join(app.config['CACHE_FOLDER'], filename)
    if not os.path.isfile(cFilepath):
        uFilenameParts = filename.rsplit('.', 1)[0].rsplit('_', 2)
        uFilename = '.'.join(uFilenameParts[0:2])
        uFilepath = os.path.join(app.config['UPLOAD_FOLDER'], uFilename)
        filetype = uFilename.rsplit('.', 1)[-1].lower()
        if filetype == 'pdf':
            pageNum = 1
            if (len(uFilenameParts) > 2):
                pageNum = int(uFilenameParts[2])
            pages = convert_from_path(uFilepath, dpi=150, jpegopt={"progressive": True, "optimize": True})
            pages[pageNum-1].save(cFilepath, quality=35)
        if filetype == 'jpg' or filetype == 'jpeg' or filetype == 'png':
            img = Image.open(uFilepath)
            if filetype == 'png':
                img = img.convert('RGB')
            img.save(cFilepath, "JPEG", quality=35, optimize=True, progressive=True)
