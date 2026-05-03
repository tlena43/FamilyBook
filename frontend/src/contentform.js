import React, { useState, useEffect, useMemo, useRef } from "react";
import "./index.css";
import {
  useInput,
  fetchContent,
  LabelInputField,
  useMonth,
  SelectField,
  validateDates,
  DateBundle,
  separateDate,
} from "./formfunctions.js";
import { apiJson, apiFetch } from "./global.js";
import { Person } from "./person.js";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "./authContext.js";
import PeopleSearch from "./peoplepicker.js";


// api helpers
export async function uploadFile(file, loginKey) {
  const formData = new FormData();
  formData.append("upload", file);

  return apiJson("upload", {
    loginKey,
    method: "POST",
    body: formData,
  });
}

export async function createContent(content, loginKey) {
  return apiJson("content", {
    loginKey,
    method: "POST",
    body: content,
  });
}

export async function patchContent(loginKey, id, content) {
  return apiJson("content/" + id, {
    loginKey,
    method: "PATCH",
    body: content,
  });
}

export async function deleteUpload(loginKey, file) {
  if (!file) return;

  await apiFetch("upload/" + file, {
    loginKey,
    method: "DELETE",
  });
}

export async function deleteContent(loginKey, id) {
  await apiFetch("content/" + id, {
    loginKey,
    method: "DELETE",
  });
}

// content form
const ContentForm = () => {
  const { loginKey } = useAuth(); // ✅ pull from context
  const fileRef = useRef(null);
  const navigate = useNavigate();
  const { id } = useParams();
  const editing = id !== undefined;

  const [submitting, setSubmitting] = useState(false);
  const [errorContent, setErrorContent] = useState(null);
  const [loadingContent, setLoadingContent] = useState(true);

  const { value: fileTitle, bind: bindFileTitle, reset: resetFileTitle, setValue: setFileTitle } =
    useInput("");
  const { value: notes, bind: bindNotes, reset: resetNotes, setValue: setNotes } = useInput("");
  const { value: location, bind: bindLocation, reset: resetLocation, setValue: setLocation } =
    useInput("");

  const {
    value: month,
    numDays: numDays,
    bind: bindMonth,
    reset: resetMonth,
    setValue: setMonth,
    setNumDays: setNumDays,
  } = useMonth("");

  const { value: day, bind: bindDay, reset: resetDay, setValue: setDay } = useInput("");
  const { value: year, bind: bindYear, reset: resetYear, setValue: setYear } = useInput("");

  const [selectedList, setSelectedList] = useState([]);

  const {
    value: contentType,
    bind: bindContentType,
    reset: resetContentType,
    setValue: setContentType,
  } = useInput("");

  const contentOpts = ["Newspaper", "Obituary", "Certificate", "Photo", "Legal Documents", "Other"];

  const [storedFile, setStoredFile] = useState("");
  const [isUploading, setIsUploading] = useState("");


  useEffect(() => {
    if (!loginKey) return;

    if (!editing) {
      setLoadingContent(false);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        setLoadingContent(true);
        setErrorContent(null);

        const contentEdit = await fetchContent(id, loginKey);
        if (cancelled) return;

        setFileTitle(contentEdit.title ?? "");
        setNotes(contentEdit.notes ?? "");
        setLocation(contentEdit.location ?? "");

        const contentDate = separateDate(contentEdit.date, contentEdit.dateUnknowns);
        setMonth(contentDate.month ?? "");
        setDay(contentDate.day ?? "");
        setYear(contentDate.year ?? "");
        setNumDays(contentDate.daysNum);

        setContentType(contentEdit.type ?? "");

        setStoredFile(contentEdit.fileName ?? "");

        const mapRes = (contentEdit.people ?? []).map((p) => new Person(p));
        setSelectedList(mapRes);
      } catch (e) {
        if (!cancelled) setErrorContent(e);
      } finally {
        if (!cancelled) setLoadingContent(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    editing,
    id,
    loginKey,
    setContentType,
    setDay,
    setFileTitle,
    setLocation,
    setMonth,
    setNotes,
    setNumDays,
    setYear,
  ]);

  function resetStates() {
    resetFileTitle();
    resetNotes();
    resetLocation();
    resetMonth();
    resetDay();
    resetYear();
    resetContentType();
    setSelectedList([]);
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);

    try {
      let alertStr = "";
      const contentDateFull = validateDates(month, day, year);

      if ((fileTitle ?? "").length > 50) alertStr += "Title can not exceed 50 characters\n";
      if ((fileTitle ?? "").trim() === "") alertStr += "Title can not be blank\n";
      if (contentDateFull[0] === false) alertStr += "Your date is invalid. " + contentDateFull[1] + "\n";

      const file = fileRef.current?.files?.[0];
      if (!editing && !file) alertStr += "A file must be uploaded\n";

      if (alertStr) {
        alert(alertStr);
        return;
      }

      const selectedListID = selectedList.map((p) => p.id);

      const content = {
        user: 1,
        type: contentOpts.indexOf(contentType) + 1,
        date: contentDateFull[1],
        notes: (notes ?? "").trim(),
        title: (fileTitle ?? "").trim(),
        people: selectedListID,
        location: (location ?? "").trim(),
        dateUnknowns: contentDateFull[0],
      };

      setIsUploading("loader");

      if (!editing) {
        const uploadData = await uploadFile(file, loginKey);
        content.file = uploadData.fileid;

        const created = await createContent(content, loginKey);

        resetStates();
        navigate("/content/" + created.id);
        return;
      }

      const updated = await patchContent(loginKey, id, content);

      resetStates();
      const nextId = updated?.id ?? id;
      navigate("/content/" + nextId);
    } catch (err) {
      console.error("Submit failed:", err);
      alert("There has been a problem with your submit. Check console for details.");
    } finally {
      if (fileRef.current) fileRef.current.value = null;
      setIsUploading("");
      setSubmitting(false);
    }
  };

  if (errorContent) return "Failed to load resource A";

  return (
    <div className={isUploading}>
      <div className="loader-bar"></div>

      <div className="form-style">
        <h1>Add a Document</h1>

        <form onSubmit={handleSubmit} id="content-form">
          <div className="section">
            <span>1</span>Upload a file
          </div>

          <div className="inner-wrap">
            {editing ? (
              <p>Can not edit files</p>
            ) : (
              <input ref={fileRef} type="file" id="content-file" name="filename" />
            )}

            <LabelInputField binding={bindFileTitle} label={"Add a Title"} id={"file-title"} />
          </div>

          <div className="section">
            <span>2</span>Who is this document about?
          </div>

          <div className="inner-wrap">
            <PeopleSearch
              selectedList={selectedList}
              setSelectedList={setSelectedList}
              loginKey={loginKey}
              maxSelect={null}
            />
          </div>

          <div className="section">
            <span>3</span>Optional details
          </div>

          <div className="inner-wrap">
            <SelectField
              binding={bindContentType}
              id={"content-type-select"}
              label={"Content Type"}
              array={contentOpts}
            />
            <LabelInputField binding={bindNotes} label={"Notes"} id={"content-notes"} type={"textarea"} />
            <LabelInputField binding={bindLocation} label={"Location"} id={"content-location"} type={"text"} />
            <DateBundle
              label={"Date"}
              binding={[bindYear, bindMonth, bindDay]}
              id={["content-year", "content-month", "content-day"]}
              num={numDays}
              show={true}
            />
          </div>

          <input type="submit" value={submitting ? "Submitting..." : "Submit"} disabled={submitting} />

          {editing ? (
            <button
              type="button"
              className="delete-btn"
              onClick={async () => {
                try {
                  setIsUploading("loader");
                  await deleteContent(loginKey, id);
                  await deleteUpload(loginKey, storedFile);
                  navigate("/content");
                } catch (err) {
                  console.error("Delete failed:", err);
                  alert("Delete failed. Check console for details.");
                } finally {
                  setIsUploading("");
                }
              }}
            >
              Delete
            </button>
          ) : null}
        </form>
      </div>
    </div>
  );
};

export default ContentForm;