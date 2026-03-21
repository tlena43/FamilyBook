import React, { useState, useEffect, useMemo } from "react";
import "./index.css";
import { apiJson } from "./global.js";
import { Person } from "./person.js";

const monthList = [
  "Unknown","January","February","March","April","May","June",
  "July","August","September","October","November","December",
];
const dayList = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

// start form functions
function ValidateFebruary(year, day) {
  if (day === 29) {
    if (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)) {
      return true;
    }
    return false;
  }
  return true;
}

export const validateDates = (month, day, year) => {
  const isFebValid = ValidateFebruary(year, day);
  if (!isFebValid) {
    return [false, "You selected February 29th without a leap year!"];
  }

  const today = new Date();
  const inputDateInfo = processDate(month, day, year);

  if (inputDateInfo[1] <= today) {
    return inputDateInfo;
  }

  return [false, "Your date can't be in the future!"];
};

export const useInput = (initialValue) => {
  const [value, setValue] = useState(initialValue);

  return {
    value,
    setValue,
    reset: () => setValue(""),
    bind: {
      value,
      onChange: (event) => {
        setValue(event.target.value);
      },
    },
  };
};

export const useMonth = (initialValue) => {
  const [value, setValue] = useState(initialValue);
  const [numDays, setNumDays] = useState(0);

  return {
    value,
    setValue,
    numDays,
    setNumDays,
    reset: () => {
      setValue("");
      setNumDays(0);
    },
    bind: {
      value,
      numDays,
      onChange: (e) => {
        const curMonth = e.target.value;
        setValue(curMonth);

        if (curMonth !== "Unknown") {
          const monthIndex = monthList.indexOf(curMonth) - 1;
          setNumDays(dayList[monthIndex]);
        } else {
          setNumDays(0);
        }
      },
    },
  };
};

export const CheckBox = (initialValue) => {
  const [value, setValue] = useState(initialValue);
  const [checked, setChecked] = useState(false);

  return {
    value,
    setValue,
    checked,
    setChecked,
    reset: () => {
      setValue("");
      setChecked(false);
    },
    bind: {
      value,
      onChange: (event) => {
        setValue(event.target.value);
        setChecked((prev) => !prev);
      },
    },
  };
};

function processDate(month, day, year) {
  let unknowns = 0;
  let date;

  if (year === "") {
    unknowns = 3;
    date = null;
  } else if (month === "Unknown" || month === "") {
    unknowns = 2;
    date = new Date(year, 0, 1);
  } else if (day === "Unknown" || day === "") {
    unknowns = 1;
    date = new Date(year, monthList.indexOf(month) - 1, 1);
  } else {
    date = new Date(year, monthList.indexOf(month) - 1, day);
  }

  return [unknowns, date];
}

export const unpackDate = (date, unknowns) => {
  let stringDate = "";
  const monthIndex = date.getUTCMonth();

  if (unknowns === 0) {
    stringDate =
      monthList[monthIndex + 1] +
      " " +
      date.getUTCDate() +
      " " +
      date.getUTCFullYear();
  } else if (unknowns === 1) {
    stringDate = monthList[monthIndex + 1] + " " + date.getUTCFullYear();
  } else if (unknowns === 2) {
    stringDate = String(date.getUTCFullYear());
  } else {
    stringDate = "Date Unknown";
  }

  return stringDate;
};

async function fetchGender() {
  const data = await apiJson("gender", {
    method: "GET",
  });

  return data.genders;
}

export const ProcessGender = ({ setGender, gender }) => {
  const [valueGender, setValueGender] = useState(null);
  const [errorGender, setErrorGender] = useState(null);
  const [loadingGender, setLoadingGender] = useState(true);

  async function getGender() {
    try {
      setLoadingGender(true);
      const genders = await fetchGender(); // keep your existing fetchGender (or apiJson version)
      setValueGender(genders);
    } catch (e) {
      setErrorGender(e);
    } finally {
      setLoadingGender(false);
    }
  }

  useEffect(() => {
    getGender();
  }, []);

  const handleRadioChange = (e) => {
    setGender(e.target.value); // store as string (safe)
  };

  if (errorGender) return "Failed to load resource A";

  return loadingGender ? (
    "Loading..."
  ) : (
    <div>
      <label id="gender-label">Gender:</label>
      <div className="radio-group">
        {(valueGender ?? []).map((i) => {
          const idStr = String(i.id);
          const genderStr = String(gender ?? "");

          return (
            <div className="label-input-field" key={i.name}>
              <label htmlFor={`gender-${idStr}`}>
                <input
                  type="radio"
                  name="gender"
                  id={`gender-${idStr}`}
                  value={idStr}
                  checked={genderStr === idStr}
                  onChange={handleRadioChange}
                  className="radio-box"
                />
                {i.name}
              </label>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const DateBundle = ({ label, binding, id, num, show }) => {
  if (show === false) {
    return <div></div>;
  }
  return (
    <div className="date-bundle">
      {/* <p>{label}</p> */}
      <LabelInputField binding={binding[0]} label={"Year"} type={"text"} id={id[0]} />
      <SelectField binding={binding[1]} id={id[1]} array={monthList} label={"Month"} />
      <DayField num={num} id={id[2]} binding={binding[2]} />
    </div>
  );
};

export const separateDate = (date, unknowns) => {
  // date can be null if unknowns === 3 (or backend sends null)
  const dateObj = date ? new Date(date) : null;

  let month = "";
  let day = "";
  let year = "";
  let daysNum = 0;

  if (dateObj) {
    month = monthList[dateObj.getUTCMonth() + 1];  // "January"..."December"
    daysNum = dayList[dateObj.getUTCMonth()];
    day = String(dateObj.getUTCDate());           // keep as string for <select>
    year = String(dateObj.getUTCFullYear());
  }

  // Apply unknowns flags in the SAME format your UI expects
  if (unknowns >= 1) {
    day = "Unknown";
  }
  if (unknowns >= 2) {
    month = "Unknown";
    daysNum = 0; // day dropdown should collapse when month unknown
  }
  if (unknowns === 3) {
    year = "";
    month = "Unknown";
    day = "Unknown";
    daysNum = 0;
  }

  return { month, day, year, daysNum };
};

function DayField({ num, binding }) {
  if (num > 0) {
    return (
      <div className="day-field">
        <label htmlFor="day">Day</label>
        <select id="day" name="day" {...binding} className="box-input" defaultValue="">
          <option value="" disabled hidden>
            Select
          </option>
          <option value="Unknown">Unknown</option>
          {Array.from({ length: num }, (_, i) => (
            <option key={i + 1} value={i + 1}>
              {i + 1}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return <div></div>;
}

export const LabelInputField = ({ binding, label, type, id, name, value, onChange }) => {
  if (type === "checkbox") {
    return (
      <div className="label-input-field">
        <label htmlFor={id} className="checkbox-label">
          {label}
          <input type={type} name={name} {...binding} id={id} value={value} />
        </label>
      </div>
    );
  }

  if (type === "radio") {
    return (
      <div className="label-input-field ">
        <label htmlFor={id}>
          <input
            type={type}
            name={name}
            {...binding}
            id={id}
            value={value}
            onChange={onChange}
            className="radio-box"
          />
          {label}
        </label>
      </div>
    );
  }

  if (type === "textarea") {
    return (
      <div className="label-input-field">
        <label htmlFor={id}>
          {label}
          <textarea {...binding} id={id} className="box-input" />
        </label>
      </div>
    );
  }

  return (
    <div className="label-input-field">
      <label htmlFor={id}>
        {label}
        <input type={type} {...binding} id={id} className="box-input" />
      </label>
    </div>
  );
};

export const SelectField = ({ binding, array, id, label }) => {
  return (
    <div className="select-container">
      <label htmlFor={id}>
        {label}
        <select id={id} name={id} {...binding} className="box-input " defaultValue="">
          <option value="" disabled hidden>
            Select
          </option>
          {array.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
};

export const fetchPeople = async (loginKey) => {
  const data = await apiJson("person", {
    loginKey,
    method: "GET",
  });

  return data?.people ?? [];
};

export const fetchPerson = async (id, loginKey) => {
  return apiJson("person/" + id, {
    loginKey,
    method: "GET",
  });
};

export const fetchContent = async (id, loginKey) => {
  return apiJson("content/" + id, {
    loginKey,
    method: "GET",
  });
};

function SearchList({ filteredPersons, selectedList, setSelectedList }) {
  const filtered = filteredPersons.map((person) => (
    <PersonDisplay
      key={person.id}
      person={new Person(person)}
      selectedList={selectedList}
      setSelectedList={setSelectedList}
    />
  ));

  return <div>{filtered}</div>;
}

// people picker
function PersonDisplay({ person, selectedList, setSelectedList }) {
  const isSelected = selectedList.some((p) => p.id === person.id);

  function personDisplayClick() {
    if (isSelected) {
      setSelectedList(selectedList.filter((item) => item.id !== person.id));
    } else {
      setSelectedList((arr) => [...arr, person]);
    }
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

export function PeopleSearch({ people, selectedList, setSelectedList, isLoading, error }) {
  const [searchField, setSearchField] = useState("");

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

  if (error) return "Failed to load resource A";
  if (isLoading) return "Loading...";

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
        />
      </Scroll>

      <label id="selected-label" htmlFor="selected-list">
        Selected People
      </label>
      <ul id="selected-list">{selectedPeople}</ul>
    </section>
  );
}
// end form functions