import React, { useState, useEffect, useRef } from "react";
import "./index.css";
import {
  useInput,
  SelectField,
  separateDate,
  fetchPerson,
  LabelInputField,
  useMonth,
  validateDates,
  DateBundle,
  CheckBox,
  ProcessGender,
} from "./formfunctions.js";
import { useParams, useNavigate } from "react-router-dom";
import { Person } from "./person";
import { apiFetch, apiJson } from "./global.js";
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
  }); // { fileid }
}

export async function createPerson(person, loginKey) {
  return apiJson("person", {
    loginKey,
    method: "POST",
    body: person,
  }); // { id }
}

export async function patchPerson(person, loginKey, id) {
  await apiFetch("person/" + id, {
    loginKey,
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(person),
  });

  return true;
}

export async function deleteUploadIfNeeded(loginKey, fileName) {
  if (!fileName) return;

  await apiFetch("upload/" + fileName, {
    loginKey,
    method: "DELETE",
  });
}

export async function deletePerson(loginKey, id) {
  await apiFetch("person/" + id, {
    loginKey,
    method: "DELETE",
  });

  return true;
}


// person form
const PersonForm = () => {
  const { loginKey } = useAuth();
  const fileRef = useRef(null);
  const navigate = useNavigate();
  const { id } = useParams();
  const editing = id !== undefined;

  const [valuePerson, setValuePerson] = useState(null);
  const [errorPerson, setErrorPerson] = useState(null);
  const [loadingPerson, setLoadingPerson] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [people, setPeople] = useState([]);
  const [loadingPeople, setLoadingPeople] = useState(true);
  const [errorPeople, setErrorPeople] = useState(null);
  const [selectedListParent, setSelectedListParent] = useState([]);
  const [selectedListChild, setSelectedListChild] = useState([]);
  const [selectedListSpouse, setSelectedListSpouse] = useState([]);



  const { value: firstName, bind: bindFirstName, reset: resetFirstName, setValue: setFirstName } =
    useInput("");
  const { value: middleName, bind: bindMiddleName, reset: resetMiddleName, setValue: setMiddleName } =
    useInput("");
  const { value: lastName, bind: bindLastName, reset: resetLastName, setValue: setLastName } =
    useInput("");
  const { value: birthplace, bind: bindBirthplace, reset: resetBirthplace, setValue: setBirthPlace } =
    useInput("");

  const {
    value: birthMonth,
    numDays: numDays,
    setNumDays: setNumDaysBirth,
    bind: bindBirthMonth,
    reset: resetBirthMonth,
    setValue: setBirthMonth,
  } = useMonth("");

  const { value: birthDay, bind: bindBirthDay, reset: resetBirthDay, setValue: setBirthDay } =
    useInput("");
  const { value: birthYear, bind: bindBirthYear, reset: resetBirthYear, setValue: setBirthYear } =
    useInput("");

  const {
    value: deathMonth,
    numDays: numDaysDeath,
    setNumDays: setNumDaysDeath,
    bind: bindDeathMonth,
    reset: resetDeathMonth,
    setValue: setDeathMonth,
  } = useMonth("");

  const { value: deathDay, bind: bindDeathDay, reset: resetDeathDay, setValue: setDeathDay } =
    useInput("");
  const { value: deathYear, bind: bindDeathYear, reset: resetDeathYear, setValue: setDeathYear } =
    useInput("");

  const { checked: isDeadChecked, setChecked: setIsDeadChecked, bind: bindIsDead, reset: resetIsDead } =
    CheckBox("");

  const [gender, setGender] = useState("");
  const { value: privacy, bind: bindPrivacy, setValue: setPrivacy } = useInput("");
  const { value: maidenName, bind: bindMaidenName, reset: resetMaidenName, setValue: setMaidenName } =
    useInput("");

  const [isUploading, setIsUploading] = useState("");
  const [originalFile, setOriginalFile] = useState("");

  const privacyOpts = ["Admin Only", "Close Family", "Extended Family"];

  function resetForm() {
    resetFirstName();
    resetLastName();
    resetMiddleName();
    resetBirthplace();
    resetBirthMonth();
    resetBirthDay();
    resetBirthYear();
    resetDeathMonth();
    resetDeathDay();
    resetDeathYear();
    resetIsDead();
    setGender("");
    resetMaidenName();
  }

  useEffect(() => {
    if (!editing) return;
    if (!loginKey) return;

    let cancelled = false;

    (async () => {
      try {
        setLoadingPerson(true);
        setErrorPerson(null);

        const personEdit = await fetchPerson(id, loginKey);
        if (cancelled) return;

        setValuePerson(new Person(personEdit));

        setFirstName(personEdit.firstName ?? "");
        setLastName(personEdit.lastName ?? "");
        setMiddleName(personEdit.middleName ?? "");
        setBirthPlace(personEdit.birthplace ?? "");
        setMaidenName(personEdit.maidenName ?? "");
        setGender(personEdit.gender ?? "");
        setOriginalFile(personEdit.fileName ?? "");

        const birthDate = separateDate(personEdit.birthDay, personEdit.birthDateUnknowns);
        setBirthMonth(birthDate.month ?? "");
        setBirthDay(birthDate.day ?? "");
        setBirthYear(birthDate.year ?? "");
        setNumDaysBirth(birthDate.daysNum);

        const deathDate = separateDate(personEdit.deathDay, personEdit.deathDateUnknowns);
        setDeathMonth(deathDate.month ?? "");
        setDeathDay(deathDate.day ?? "");
        setDeathYear(deathDate.year ?? "");
        setNumDaysDeath(deathDate.daysNum);

        setIsDeadChecked(!!personEdit.isDead);
        setPrivacy(privacyOpts[(personEdit.privacy ?? 1) - 1] ?? "");
      } catch (e) {
        if (!cancelled) setErrorPerson(e);
      } finally {
        if (!cancelled) setLoadingPerson(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [editing, id, loginKey]);

  const handleSubmit = async (evt) => {
    evt.preventDefault();
    if (submitting) return;
    setSubmitting(true);

    let birthDateFull = [3, null];
    let deathDateFull = [3, null];

    try {
      // Validate
      let alertStr = "";

      birthDateFull = validateDates(birthMonth, birthDay, birthYear);
      deathDateFull = isDeadChecked ? validateDates(deathMonth, deathDay, deathYear) : [3, null];

      if (birthDateFull[0] === false) alertStr += "Your birth date is invalid. " + birthDateFull[1] + "\n";
      if (deathDateFull[0] === false) alertStr += "Your death date is invalid. " + deathDateFull[1] + "\n";

      if ((firstName ?? "").trim() === "") alertStr += "First name cannot be blank\n";
      if ((lastName ?? "").trim() === "") alertStr += "Last name cannot be blank\n";
      if (privacyOpts.indexOf(privacy) === -1) alertStr += "A privacy level must be selected\n";
      if ((gender ?? "") === "") alertStr += "A gender must be selected\n";

      if (alertStr) {
        alert(alertStr);
        return;
      }

      // Build person object
      const person = {
        birthDay: birthDateFull[1],
        birthDateUnknowns: birthDateFull[0],
        deathDay: deathDateFull[1],
        deathDateUnknowns: deathDateFull[0],
        birthplace: (birthplace ?? "").trim(),
        parent1: "",
        parent2: "",
        firstName: (firstName ?? "").trim(),
        lastName: (lastName ?? "").trim(),
        gender: gender,
        isDead: isDeadChecked,
        middleName: (middleName ?? "").trim(),
        maidenName: (maidenName ?? "").trim(),
        file: "",
        privacy: privacyOpts.indexOf(privacy) + 1,
      };

      // Upload + create/patch
      setIsUploading("loader");
      setErrorPerson(null);

      const file = fileRef.current?.files?.[0];

      if (file) {
        const uploadData = await uploadFile(file, loginKey);
        person.file = uploadData.fileid ?? "";
        if (fileRef.current) fileRef.current.value = null;
      }

      if (!editing) {
        const created = await createPerson(person, loginKey);
        navigate("/person/" + created.id);

        // Reset after success
        resetForm();

        return;
      }

      await patchPerson(person, loginKey, id);

      if (originalFile !== "" && person.file !== "") {
        await deleteUploadIfNeeded(loginKey, originalFile);
      }

      navigate("/person/" + id);

      // Reset after success
      resetForm();
    } catch (e) {
      console.error("Submit failed:", e);
      setErrorPerson(e);
      alert("There was a problem submitting this person. Check console for details.");
    } finally {
      setIsUploading("");
      setSubmitting(false);
    }
  };

  return (
    <div className={isUploading}>
      <div className="loader-bar"></div>

      <div className="form-style">
        <h1>Add a family member</h1>

        {errorPerson ? <p>Failed to load person info.</p> : null}

        <form onSubmit={handleSubmit} id="person-form">
          <div className="section">
            <span>1</span>Name
          </div>

          <div className="inner-wrap">
            <label htmlFor="person-file">
              Photo:
              <input ref={fileRef} type="file" id="person-file" name="filename" />
            </label>

            <LabelInputField binding={bindFirstName} label={"First:"} type={"text"} id={"first-name"} />
            <LabelInputField binding={bindMiddleName} label={"Middle:"} type={"text"} id={"middle-name"} />
            <LabelInputField binding={bindLastName} label={"Last:"} type={"text"} id={"last-name"} />
            <LabelInputField binding={bindMaidenName} label={"Maiden Name:"} type={"text"} id={"maiden-name"} />

            <SelectField binding={bindPrivacy} id={"privacy-select"} label={"Privacy Level"} array={privacyOpts} />
            <ProcessGender gender={gender} setGender={setGender} />
          </div>

          <div className="section">
            <span>2</span>Birth
          </div>

          <div className="inner-wrap">
            <LabelInputField binding={bindBirthplace} label={"Birthplace:"} type={"text"} id={"birthplace"} />
            <DateBundle
              label={"Birth"}
              binding={[bindBirthYear, bindBirthMonth, bindBirthDay]}
              id={["birth-year", "birth-month", "birth-day"]}
              num={numDays}
              show={true}
            />
          </div>
          <div className="section">
            <span>3</span>Family
          </div>
          <div className="inner-wrap">
            <label>Parents</label>
            <PeopleSearch
              selectedList={selectedListParent}
              setSelectedList={setSelectedListParent}
              loginKey={loginKey}
              maxSelect={2}
            />
            <label>Children</label>
            <PeopleSearch
              selectedList={selectedListChild}
              setSelectedList={setSelectedListChild}
              loginKey={loginKey}
              maxSelect={null}
            />
            <label>Spouse</label>
            <PeopleSearch
              selectedList={selectedListSpouse}
              setSelectedList={setSelectedListSpouse}
              loginKey={loginKey}
              maxSelect={1}
            />
          </div>

          <div className="section">
            <span>4</span>Death
          </div>

          <div className="inner-wrap">
            <LabelInputField
              binding={bindIsDead}
              label={"Is the individual deceased?"}
              type={"checkbox"}
              id={"is-dead"}
              value={"is-dead"}
            />

            <DateBundle
              label={"Death"}
              binding={[bindDeathYear, bindDeathMonth, bindDeathDay]}
              id={["death-year", "death-month", "death-day"]}
              num={numDaysDeath}
              show={isDeadChecked}
            />
          </div>

          <input type="submit" value="Submit" />

          {editing ? (
            <button
              type="button"
              className="delete-btn"
              onClick={async () => {
                try {
                  setIsUploading("loader");
                  await deletePerson(loginKey, id);
                  await deleteUploadIfNeeded(loginKey, originalFile);
                  navigate("/person");
                } catch (e) {
                  console.error("Delete failed:", e);
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

export default PersonForm;