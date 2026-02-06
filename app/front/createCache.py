from models import *
from utilities import *
from main import *

db.connect()
for u in Upload.select():
    fileparts = u.filename.rsplit('.', 1)
    filetype = fileparts[-1].lower()
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], u.filename)
    if filetype == 'pdf':
        pages = convert_from_path(filepath)
        for i in range(len(pages)):
            cacheFilename = fileparts[0] + "_" + filetype + "_" + str(i) + ".jpg"
            print("creating cache file " + cacheFilename)
            makeCachedUpload(app, cacheFilename)
    if filetype == 'jpg' or filetype == 'jpeg' or filetype == 'png':
        cacheFilename = fileparts[0] + "_" + filetype + ".jpg"
        print("creating cache file " + cacheFilename)
        makeCachedUpload(app, cacheFilename)
db.close()
