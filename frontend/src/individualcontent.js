import React, { useState, useEffect } from "react";
import "./index.css";
import { unpackDate, fetchContent } from "./formfunctions.js";
import { deleteUpload, deleteContent } from "./contentform.js";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, apiJson } from "./global.js";
import { useAuth } from "./authContext.js";

/*
A page to provide a detailed view of one content item
*/

const IndividualContent = ({ admin }) => {
  const { loginKey } = useAuth();
  const { id } = useParams();
  const navigate = useNavigate();

  const [valueContent, setValueContent] = useState(null);
  const [errorContent, setErrorContent] = useState(null);
  const [loadingContent, setLoadingContent] = useState(true);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this content? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await deleteContent(loginKey, id);
      await deleteUpload(loginKey, valueContent?.fileName);
      navigate("/content");
    } catch (e) {
      console.error("Delete failed:", e);
      alert("Delete failed. Check console for details.");
      setDeleting(false);
    }
  };

  useEffect(() => {
    if (!loginKey) return;

    let cancelled = false;

    (async () => {
      try {
        setLoadingContent(true);
        setErrorContent(null);

        const content = await fetchContent(id, loginKey);
        if (cancelled) return;

        setValueContent(content);
      } catch (e) {
        if (!cancelled) setErrorContent(e);
      } finally {
        if (!cancelled) setLoadingContent(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id, loginKey]);

  if (errorContent) return "Failed to load resource A";

  return loadingContent ? (
    <div className="loader">
      <div className="loader-bar"></div>
    </div>
  ) : (
    <div>
      {valueContent ? (
        <ContentDisplay
          content={valueContent}
          id={id}
          admin={admin}
          onDelete={handleDelete}
          deleting={deleting}
          loginKey={loginKey}
        />
      ) : null}
    </div>
  );
};

function ContentDisplay({ content, id, admin, onDelete, deleting, loginKey }) {
  const date = unpackDate(new Date(content.date), content.dateUnknowns);

  const people = (content.people ?? []).map((person) => (
    <Link to={"/person/" + person.id} key={person.id}>
      <p>
        {person.firstName} {person.middleName} {person.lastName}
      </p>
    </Link>
  ));

  const fileName = content.fileName ?? "";
  const ext = fileName.split(".").pop()?.toLowerCase();

  return (
    <div className="individual-content-page form-style">
      <h1>{content.title}</h1>

      <div className="inner-wrap">
        {!fileName ? null : ext === "pdf" ? (
          <div className="pdf-preview">
            <PDFViewer fileName={fileName} loginKey={loginKey} />
          </div>
        ) : (
          <img alt="Content" src={api + "upload/" + fileName} />
        )}

        {!fileName ? null : (
          <a href={api + "upload/" + fileName} download>
            <p>Download</p>
          </a>
        )}

        <p>Date: {date}</p>

        {content.people?.length ? <p>People Involved:</p> : null}
        {people}

        {content.type ? <p>Content Type: {content.type}</p> : null}
        {content.notes ? <p>Notes: {content.notes}</p> : null}
        {content.location ? <p>Location: {content.location}</p> : null}

        {admin ? (
          <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
            <Link to={"/content/edit/" + id}>
              <button>Edit</button>
            </Link>
            <button
              className="delete-btn"
              onClick={onDelete}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function StackedImage({ src, loaded, setLoaded }) {
  return (
    <div>
      {loaded ? null : <div>Loading...</div>}
      <img
        style={loaded ? {} : { display: "none" }}
        src={src}
        onLoad={() => setLoaded(true)}
        alt="Content"
      />
    </div>
  );
}

async function fetchNumPages(fileName, loginKey) {
  return apiJson("upload/num_pages/" + fileName, {
    loginKey,
    method: "GET",
  });
}

function PDFViewer({ fileName, loginKey }) {
  const [numPages, setNumPages] = useState();
  const [pageNumber, setPageNumber] = useState(1);

  const [loaded, setLoaded] = useState(false);
  const [errorNumPages, setErrorNumPages] = useState(null);
  const [loadingNumPages, setLoadingNumPages] = useState(true);

  useEffect(() => {
    if (!fileName) return;

    let cancelled = false;

    (async () => {
      try {
        setLoadingNumPages(true);
        setErrorNumPages(null);

        const data = await fetchNumPages(fileName, loginKey);
        if (cancelled) return;

        setNumPages(data?.num_pages);
      } catch (e) {
        if (!cancelled) setErrorNumPages(e);
      } finally {
        if (!cancelled) setLoadingNumPages(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [fileName]);

  function getCacheFilename(filename, pageNum) {
    const fileParts = filename.split(".");
    let cacheFilename = fileParts.slice(0, -1).join(".");
    cacheFilename += "_" + fileParts[fileParts.length - 1] + "_" + pageNum + ".jpg";
    return cacheFilename;
  }

  function changePage(offset) {
    setPageNumber((prev) => prev + offset);
    setLoaded(false);
  }

  function previousPage() {
    changePage(-1);
  }

  function nextPage() {
    changePage(1);
  }

  if (errorNumPages) return "Failed to load PDF preview";
  if (loadingNumPages) return "loading";

  return (
    <>
      <StackedImage
        src={api + "upload/cache/" + getCacheFilename(fileName, pageNumber)}
        loaded={loaded}
        setLoaded={setLoaded}
      />

      <div className="pagination-display">
        <button
          type="button"
          disabled={pageNumber <= 1}
          onClick={previousPage}
          className="pdf-nav"
        >
          Previous
        </button>

        <p>
          Page {pageNumber || (numPages ? 1 : "--")} of {numPages || "--"}
        </p>

        <button
          type="button"
          disabled={!numPages || pageNumber >= numPages}
          onClick={nextPage}
          className="pdf-nav"
        >
          Next
        </button>
      </div>
    </>
  );
}

export default IndividualContent;