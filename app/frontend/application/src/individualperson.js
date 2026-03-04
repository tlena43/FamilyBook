import React, { useEffect, useState } from "react";
import "./index.css";
import { fetchPerson } from "./formfunctions.js";
import { useParams, Link } from "react-router-dom";
import { Person } from "./person.js";
import { useAuth } from "./authContext.js";

const IndividualPerson = ({ admin }) => {
  const { loginKey } = useAuth();
  const { id } = useParams();

  const [valuePerson, setValuePerson] = useState(null);
  const [errorPerson, setErrorPerson] = useState(null);
  const [loadingPerson, setLoadingPerson] = useState(true);

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
        />
      ) : null}
    </div>
  );
};

function PersonDisplay({ person, content, admin }) {
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
        {deathDay ? <p>Death Date: {deathDay}</p> : null}

        {content?.length ? <p>Tagged Content:</p> : null}
        {contentList}

        {admin ? (
          <Link to={"/person/edit/" + person.getID()}>
            <button>Edit</button>
          </Link>
        ) : null}
      </div>
    </div>
  );
}

export default IndividualPerson;