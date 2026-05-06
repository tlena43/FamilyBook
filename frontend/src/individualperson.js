import React, { useEffect, useState } from "react";
import "./index.css";
import { fetchPerson } from "./formfunctions.js";
import { deletePerson, deleteUploadIfNeeded } from "./personform.js";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Person } from "./person.js";
import { useAuth } from "./authContext.js";

/*
A page to provide a detailed view of one person
*/


const IndividualPerson = ({ admin }) => {
  const { loginKey } = useAuth();
  const { id } = useParams();
  const navigate = useNavigate();

  const [valuePerson, setValuePerson] = useState(null);
  const [errorPerson, setErrorPerson] = useState(null);
  const [loadingPerson, setLoadingPerson] = useState(true);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this person? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await deletePerson(loginKey, id);
      await deleteUploadIfNeeded(loginKey, valuePerson?.fileName);
      navigate("/person");
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
        setLoadingPerson(true);
        setErrorPerson(null);

        const person = await fetchPerson(id, loginKey);
        if (cancelled) return;

        setValuePerson(person);
      } catch (e) {
        if (!cancelled) setErrorPerson(e);
      } finally {
        if (!cancelled) setLoadingPerson(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id, loginKey]);

  if (errorPerson) return "Failed to load resource";

  return loadingPerson ? (
    <div className="loader">
      <div className="loader-bar"></div>
    </div>
  ) : (
    <div>
      {valuePerson ? (
        <PersonDisplay
          person={new Person(valuePerson)}
          content={valuePerson.content ?? []}
          admin={admin}
          onDelete={handleDelete}
          deleting={deleting}
        />
      ) : null}
    </div>
  );
};

function PersonDisplay({ person, content, admin, onDelete, deleting }) {
  const deathDay = person.getDeathDay();

  const contentList = (content ?? []).map((item) => (
    <Link to={"/content/" + item.id} key={item.id}>
      <p>{item.title}</p>
    </Link>
  ));

  return (
    <div className="form-style">
      <h1 className="individual-name">{person.getFullName()}</h1>

      <div className="inner-wrap">
        <img className="individual-photo" alt="Profile" src={person.getFileName()} />

        {person.getBirthday() ? <p>Birth Date: {person.getBirthday()}</p> : null}
        {person.getBirthPlace() ? <p>Birth Place: {person.getBirthPlace()}</p> : null}
        {person.getMaidenName() ? <p>Maiden Name: {person.getMaidenName()}</p> : null}
        {person.getSpouse() ? <p>Spouse: {person.getSpouse()}</p> : null}
        {person.getParents()[0] ? <p>Parents: {person.getParents()[0]}</p> : null}
        {person.getParents()[1] ? <p>{person.getParents()[1]}</p> : null}

        {deathDay ? <p>Death Date: {deathDay}</p> : null}

        {content?.length ? <p>Tagged Content:</p> : null}
        {contentList}

        {admin ? (
          <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
            <Link to={"/person/edit/" + person.getID()}>
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

export default IndividualPerson;