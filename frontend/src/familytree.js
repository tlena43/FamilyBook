import React, { useState, useEffect } from 'react';
import './index.css';
import { fetchPeople } from './formfunctions';
import { useAuth } from "./authContext.js";
import PersonCard from './personcard.js';
import { Person } from './person.js';
import Flow from './flow.js';

function TreeBuilder() {
  const { loginKey } = useAuth();
  const [people, setPeople] = useState([]);
  const [loadingPeople, setLoadingPeople] = useState(true);
  const [errorPeople, setErrorPeople] = useState(null);

  useEffect(() => {
    if (!loginKey) return;

    let cancelled = false;

    (async () => {
      try {
        setLoadingPeople(true);
        setErrorPeople(null);

        const valuePeople = await fetchPeople(loginKey);
        if (cancelled) return;

        setPeople(valuePeople ?? []);
      } catch (e) {
        if (cancelled) return;
        setErrorPeople(e);
      } finally {
        if (!cancelled) setLoadingPeople(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [loginKey]);

  if (loadingPeople) {
    return <div>Loading...</div>;
  }

  if (errorPeople) {
    return <div>Failed to load people.</div>;
  }

  if (people.length === 0) {
    return <div>No people found.</div>;
  }

  return (
    <div>
    </div>
  );
}

function FamilyTree() {
  return (
    <div id="family-tree-container">
      <TreeBuilder />
    </div>
  )
}

export default FamilyTree;