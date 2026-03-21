import React, { useState, useEffect, useMemo } from "react";
import "./index.css";
import { apiJson } from "./global.js";
import { Person } from "./person.js";
import { fetchPeople } from "./formfunctions.js";


function SearchList({ filteredPersons, selectedList, setSelectedList, maxSelect, numSelected, setNumSelected }) {
    const filtered = filteredPersons.map((person) => (
        <PersonDisplay
            key={person.id}
            person={new Person(person)}
            selectedList={selectedList}
            setSelectedList={setSelectedList}
            maxSelect={maxSelect}
            numSelected={numSelected}
            setNumSelected={setNumSelected}
        />
    ));

    return <div>{filtered}</div>;
}

function PersonDisplay({ person, selectedList, setSelectedList, maxSelect, numSelected, setNumSelected }) {
    const isSelected = selectedList.some((p) => p.id === person.id);

    function personDisplayClick() {
        setSelectedList((prev) => {
            if (maxSelect != null && prev.length >= maxSelect) {
                alert(`You can only select ${maxSelect} people for this field`);
                return prev;
            }
            else{
                setNumSelected((n) => n + 1);
            }

            return [...prev, person];
        });
}

return (
    <div>
        <div
            onClick={personDisplayClick}
            className={(isSelected ? "is-selected" : "not-selected") + " search-option"}
        >
            <p className="search-name-text">{person.getFullName()}</p>
            <p className="subtext">Born: {person.getBirthday()}</p>
        </div>
    </div>
);
}

const Scroll = (props) => <div className="search-scroll">{props.children}</div>;

export default function PeopleSearch({ selectedList, setSelectedList, loginKey, maxSelect }) {
    const [searchField, setSearchField] = useState("");
    const [people, setPeople] = useState([]);
    const [loadingPeople, setLoadingPeople] = useState(true);
    const [errorPeople, setErrorPeople] = useState(null);
    const [numSelected, setNumSelected] = useState(0)

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
                if (!cancelled) setErrorPeople(e);
            } finally {
                if (!cancelled) setLoadingPeople(false);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [loginKey]);


    const filtered = useMemo(() => {
        const lowerSearchStr = searchField.toLowerCase();

        return (people ?? []).filter((person) => {
            const fn = (person.firstName ?? "").toLowerCase();
            const mn = (person.middleName ?? "").toLowerCase();
            const ln = (person.lastName ?? "").toLowerCase();

            const personWithMiddle = [fn, mn, ln].filter(Boolean).join(" ");
            const personWithoutMiddle = [fn, ln].filter(Boolean).join(" ");

            return (
                personWithMiddle.includes(lowerSearchStr) ||
                personWithoutMiddle.includes(lowerSearchStr) ||
                fn.includes(lowerSearchStr) ||
                ln.includes(lowerSearchStr) ||
                mn.includes(lowerSearchStr)
            );
        });
    }, [people, searchField]);

    function removeBtnClick(index) {
        setNumSelected((n) => n + 1);
        setSelectedList(selectedList.filter((item) => item !== selectedList[index]));
    }

    const selectedPeople = selectedList.map((person, index) => (
        <li key={person.id}>
            <button className="remove-selected-btn" onClick={() => removeBtnClick(index)} type="button">
                &#10006;
            </button>
            <p className="search-name-text">{person.getFullName()}</p>
            <p className="subtext">Born: {person.getBirthday()}</p>
        </li>
    ));

    if (errorPeople) return "Failed to load resource A";
    if (loadingPeople) return "Loading...";

    return (
        <section>
            <div>
                <input
                    type="search"
                    placeholder="Type to Search"
                    onChange={(e) => setSearchField(e.target.value)}
                    className="box-input"
                />
            </div>

            <Scroll>
                <SearchList
                    filteredPersons={filtered}
                    selectedList={selectedList}
                    setSelectedList={setSelectedList}
                    maxSelect={maxSelect}
                    numSelected={numSelected}
                    setNumSelected={setNumSelected}
                />
            </Scroll>

            <label id="selected-label" htmlFor="selected-list">
                Selected People
            </label>
            <ul id="selected-list">{selectedPeople}</ul>
        </section>
    );
}