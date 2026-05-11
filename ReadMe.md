## Family Book ReadMe

Family Book is a genealogical application that allows users to upload and store information about their family members and important family history documents. Family Book has since been extended to support multiple users, sharing of information between users, and family tree generation. Other users can be given access to view each others family trees and family trees provide the ability to trace relationships, query relationships, and search for relationships.

**Authors:** Helena Thiessen and Gloria Duo
(note: Mizzezkitty and tlena43 are both Helena's accounts)

**Last modified date:** 5/5/26

**Creation date:** 5/5/26

---  
## Setup Instructions

### To Install Dependencies:
#### The following must be downloaded and installed:
```
nodeJS			: https://nodejs.org/en/download
python 3.11+	: https://www.python.org/downloads/
sqlite			: https://sqlite.org/download.html
sass			: https://sass-lang.com/install/
swi-prolog		: https://www.swi-prolog.org/download/devel
poppler         : https://pypi.org/project/python-poppler/
```
While the production version is utilizing mySQL, the development version is configured to SQLite for ease of use. 

#### Run the following commands:


From root:
```
npm install
```

From frontend:
```
npm install
```

From backend:
```
pip install -r requirements.txt
```
---
### To initialize the database:
#### Run the following from backend:
Before these steps a database environment must be established in the database manager of your choice. 

To create the database tables:
```
python loaddb.py
```

Optional, to seed a test tree and user:
```
python testData.py
```

Optional, to seed a test family group:
```
python seed.py
```
---
### To initialize environment variables:
#### Create a .env in frontend
Set the following environment variables
```
REACT_APP_SITE_TITLE='<title>'
REACT_APP_API='<location>'
```

#### Create a .env in backend
Set the following environment variables

```
user = <db user>
pass = <db password>
host = <host>
port = <port>
secretKey = <secret key>
```
---
## Run Instructions

### To run the application

From the root folder run:
```
npm run dev
```
This concurrently starts the front end and back end to launch the application locally. If it fails to launch, check the console log to ensure that all dependencies were properly installed
