import React, { useState, useEffect } from 'react';
import './index.css';
import { fetchPeople } from './formfunctions';
import Search from './search'
import { useAuth } from "./authContext.js";

function ProcessPeople() {
  const { loginKey } = useAuth();
  const [people, setPeople] = useState([]);
  const [loadingPeople, setLoadingPeople] = useState(true);
  const [errorPeople, setErrorPeople] = useState(null);

  useEffect(() => {
    if(!loginKey) return;
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

  return (
    <div>
      <Search details={people} cardType="person" isLoading={loadingPeople} error={errorPeople} />
    </div>
  );
}

export default ProcessPeople;