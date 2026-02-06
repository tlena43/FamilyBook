import React, { useState, useEffect } from 'react';
import './index.css';
import { useInput, SelectField, separateDate, fetchPerson, LabelInputField, useMonth, validateDates, DateBundle, CheckBox, ProcessGender } from "./formfunctions.js"
import { useParams, Link } from "react-router-dom";
import { Person } from './person';
import { api } from "./global.js"


function fetchPersonPost(person, loginKey) {
  fetch(api + "person", {
    method: "POST",
    body: JSON.stringify(person),

    headers: {
      "Content-Type": "application/json",
      "X-api-key": loginKey
    }
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Response was not OK');
      }
      return response.json()
    })
    .then(data => {
      window.location = ("/person/" + data["id"])
    })
    .catch(error => {
      console.error('There has been a problem with your fetch operation:', error);
    })
}

//start person form functions
const PersonForm = ({ loginKey }) => {
  const [valuePerson, setValuePerson] = useState(null);
  const [errorPerson, setErrorPerson] = useState(null);
  const [loadingPerson, setLoadingPerson] = useState(false);
  const { value: firstName, bind: bindFirstName, reset: resetFirstName, setValue: setFirstName } = useInput("");
  const { value: middleName, bind: bindMiddleName, reset: resetMiddleName, setValue: setMiddleName } = useInput("");
  const { value: lastName, bind: bindLastName, reset: resetLastName, setValue: setLastName } = useInput('');
  const { value: birthplace, bind: bindBirthplace, reset: resetBirthplace, setValue: setBirthPlace } = useInput('');
  const { value: birthMonth, numDays: numDays, setNumDays: setNumDaysBirth, bind: bindBirthMonth, reset: resetBirthMonth, setValue: setBirthMonth } = useMonth('')
  const { value: birthDay, bind: bindBirthDay, reset: resetBirthDay, setValue: setBirthDay } = useInput('')
  const { value: birthYear, bind: bindBirthYear, reset: resetBirthYear, setValue: setBirthYear } = useInput('')
  const { value: deathMonth, numDays: numDaysDeath, setNumDays: setNumDaysDeath, bind: bindDeathMonth, reset: resetDeathMonth, setValue: setDeathMonth } = useMonth('')
  const { value: deathDay, bind: bindDeathDay, reset: resetDeathDay, setValue: setDeathDay } = useInput('')
  const { value: deathYear, bind: bindDeathYear, reset: resetDeathYear, setValue: setDeathYear } = useInput('')
  const { value: isDead, checked: isDeadChecked, setChecked: setIsDeadChecked, bind: bindIsDead, reset: resetIsDead } = CheckBox('')
  const [gender, setGender] = useState('')
  const { value: privacy, bind: bindPrivacy, setValue: setPrivacy } = useInput("")
  const { value: maidenName, bind: bindMaidenName, reset: resetMaidenName, setValue: setMaidenName } = useInput("")
  let { id } = useParams();
  const [editing, setEditing] = useState(id)
  const [isUploading, setIsUploading] = useState("")
  const [originalFile, setOriginalFile] = useState("")
  let privacyOpts = ["Admin Only", "Close Family", "Extended Family"]
  async function getPerson() {
    if (id !== undefined) {
      try {
        setLoadingPerson(true);
        const personEdit = await fetchPerson(id, loginKey)
        setValuePerson(new Person(personEdit))
        setFirstName(personEdit.firstName ? personEdit.firstName : "");
        setLastName(personEdit.lastName ? personEdit.lastName : "");
        setMiddleName(personEdit.middleName ? personEdit.middleName : "");
        setBirthPlace(personEdit.birthplace ? personEdit.birthplace : "")
        setMaidenName(personEdit.maidenName ? personEdit.maidenName : "")
        setGender(personEdit.gender)
        setOriginalFile(personEdit.fileName ? personEdit.fileName : "")
        console.log(personEdit.fileName)
        console.log(originalFile)
        document.querySelector('input[name="gender"][value ="' + personEdit.gender + '"]').checked = true
        let birthDate = separateDate(personEdit.birthDay, personEdit.birthDateUnknowns)
        setBirthMonth(birthDate.month ? birthDate.month : "")
        setBirthDay(birthDate.day ? birthDate.day : "")
        setBirthYear(birthDate.year ? birthDate.year : "")
        setNumDaysBirth(birthDate.daysNum)
        let deathDate = separateDate(personEdit.deathDay, personEdit.deathDateUnknowns)
        setDeathMonth(deathDate.month ? deathDate.month : "");
        setDeathDay(deathDate.day ? deathDate.day : "");
        setDeathYear(deathDate.year ? deathDate.year : "");
        setNumDaysDeath(deathDate.daysNum);
        setIsDeadChecked(personEdit.isDead)
        setPrivacy(privacyOpts[personEdit.privacy - 1])
        if (personEdit.isDead) {
          document.getElementById("is-dead").checked = true;
        }
      } catch (e) {
        setErrorPerson(e);
      } finally {
        setLoadingPerson(false);
      }

    }
  }
  useEffect(() => {
    getPerson();
  }, []);






  const handleSubmit = (evt) => {
    evt.preventDefault();
    // setGender(document.querySelector('input[name="gender"]:checked').value)
    // console.log(firstName, lastName,birthplace, birthMonth, birthDay, birthYear,
    //   deathDay, deathMonth, deathYear, isDead, gender )
    console.log(originalFile)
    let alertStr = ""
    let birthDateFull = validateDates(birthMonth, birthDay, birthYear);
    let deathDateFull = (isDeadChecked ? validateDates(deathMonth, deathDay, deathYear) : [3, null])
    if (birthDateFull[0] === false) {
      alertStr += ("Your birth date is invalid. " + birthDateFull[1] + "\n")
    }

    if (deathDateFull[0] === false) {
      alertStr += ("Your death date is invalid. " + deathDateFull[1] + "\n")
    }

    if (firstName === "") {
      alertStr += ("First name cannot be blank\n")
    }

    if (lastName === "") {
      alertStr += ("Last name cannot be blank\n")
    }

    if (privacyOpts.indexOf(privacy) === -1) {
      console.log(privacy)
      alertStr += "A privacy level must be selected\n"
    }

    if (gender === "") {
      alertStr += "A gender must be selected\n"
    }

    if (alertStr !== "") {
      alert(alertStr)
      return ("")
    }
    let person = {
      birthDay: birthDateFull[1], birthDateUnknowns: birthDateFull[0],
      deathDay: deathDateFull[1], deathDateUnknowns: deathDateFull[0],
      birthplace: birthplace.trim(), parent1: "", parent2: "",
      firstName: firstName.trim(), lastName: lastName.trim(), gender: gender,
      isDead: isDeadChecked, middleName: middleName.trim(), maidenName: maidenName.trim(), file: "",
      privacy: (privacyOpts.indexOf(privacy) + 1)
    }


    console.log(person)
    resetFirstName();
    resetLastName();
    resetMiddleName();
    resetBirthplace();
    document.querySelector('input[name="gender"]:checked').checked = false;
    resetBirthMonth();
    resetBirthDay();
    resetBirthYear();
    resetDeathMonth();
    resetDeathDay();
    resetDeathYear();
    resetIsDead();
    document.getElementById("is-dead").checked = false;
    setGender("")
    resetMaidenName();


    setIsUploading("loader")
    const fileField = document.getElementById("person-file");
    const formData = new FormData();
    formData.append("upload", fileField.files[0])


    if (!editing) {
      if (fileField.files.length === 0) {
        fetchPersonPost(person, loginKey)
      }
      else {
        fileField.value = null;
        fetch(api + "upload", {
          method: "POST",
          body: formData,

          headers: {
            "X-api-key": loginKey
          }
        })
          .then(response => {
            if (!response.ok) {
              throw new Error('Response was not OK');
            }
            return response.json()
          })
          .then(data => {
            person["file"] = data["fileid"]
            fetchPersonPost(person, loginKey)
          })
          .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
          })
      }
    }

    else {
      console.log(fileField.files.length)
      if (fileField.files.length === 0) {
        personPatch(person, loginKey, id, originalFile)
      }
      else {
        fileField.value = null;
        fetch(api + "upload", {
          method: "POST",
          body: formData,

          headers: {
            "X-api-key": loginKey
          }
        })
          .then(response => {
            if (!response.ok) {
              throw new Error('Response was not OK');
            }
            return response.json()
          })
          .then(data => {
            person["file"] = data["fileid"]
            personPatch(person, loginKey, id, originalFile)

          })
          .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
          })
      }
    }






  }
  // console.log(errorPerson)

  // if (errorPerson) return "failed to load resource";
  // return loadingPerson ? <div className="loader" >
  // <div className='loader-bar' ></div></div>  : 
  return(
    <div className={isUploading} >
      <div className='loader-bar' ></div>
      <div className="form-style">

        <h1>Add a family member</h1>
        <form onSubmit={handleSubmit} id="person-form">
          <div className="section"><span>1</span>Name</div>
          <div className="inner-wrap">

            <label for="person-file">Photo:
              <input type="file" id="person-file" name="filename" /></label>

            <LabelInputField binding={bindFirstName} label={"First:"} type={"text"} id={"first-name"} />
            <LabelInputField binding={bindMiddleName} label={"Middle:"} type={"text"} id={"middle-name"} />
            <LabelInputField binding={bindLastName} label={"Last:"} type={"text"} id={"last-name"} />
            <LabelInputField binding={bindMaidenName} label={"Maiden Name:"} type={"test"} id={"maiden-name"} />
            <SelectField binding={bindPrivacy} id={"privacy-select"} label={"Privacy Level"} array={privacyOpts} /> 
            <ProcessGender setGender={setGender} />
          </div>
          <div className="section"><span>2</span>Birth</div>
          <div className="inner-wrap">
            <LabelInputField binding={bindBirthplace} label={"Birthplace:"} type={"text"} id={"birthplace"} />
            <DateBundle label={"Birth"} binding={[bindBirthYear, bindBirthMonth, bindBirthDay]}
              id={["birth-year", "birth-month", "birth-day"]} num={numDays} show={true} />
          </div>
          <div className="section"><span>3</span>Death</div>
          <div className="inner-wrap">
            <LabelInputField binding={bindIsDead} label={"Is the individual deceased?"} type={"checkbox"} id={"is-dead"} value={"is-dead"} />
            <DateBundle label={"Death"} binding={[bindDeathYear, bindDeathMonth, bindDeathDay]}
              id={["death-year", "death-month", "death-day"]} num={numDaysDeath} show={isDeadChecked} />
          </div>
          <input type="submit" value="Submit" />
          {editing ? <button type="button" className='delete-btn' onClick={() => personDelete(loginKey, id, originalFile)}>Delete</button> : <></>}
        </form>
      </div>
    </div>
  );
}

function personPatch(person, loginKey, id, originalFile) {
  fetch(api + "person/" + id, {
    method: "PATCH",
    body: JSON.stringify(person),
    headers: {
      "X-api-key": loginKey,
      "Content-Type": "application/json",
    }
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Response was not OK');
      }
      if (originalFile !== "" && person["file"] !== "") {
        console.log(originalFile)
        fetch(api + "upload/" + originalFile, {
          method: "DELETE",
          headers: {
            "X-api-key": loginKey,
            "Content-Type": "application/json",
          }
        })
          .then(response => {
            if (!response.ok) {
              throw new Error('Response was not OK');
            }
            return response.json()
          })
          .then(data => {
            window.location = ("/person/" + id)
          })
          .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
          })
      }
      else {
        window.location = ("/person/" + id)
      }
    })
    .catch(error => {
      console.error('There has been a problem with your fetch operation:', error);
    })
}

function personDelete(loginKey, id, file) {
  fetch(api + "person/" + id, {
    method: "DELETE",
    headers: {
      "X-api-key": loginKey,
      "Content-Type": "application/json",
    }
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Response was not OK');
      }
      if (file !== "") {
        fetch(api + "upload/" + file, {
          method: "DELETE",
          headers: {
            "X-api-key": loginKey,
            "Content-Type": "application/json",
          }
        })
          .then(response => {
            if (!response.ok) {
              throw new Error('Response was not OK');
            }
            return response.json()
          })
          .then(data => {
            window.location = ("/person")
          })
          .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
          })
      }
      else {
        window.location = ("/person/" + id)
      }
    })
    .catch(error => {
      console.error('There has been a problem with your fetch operation:', error);
    })
}

export default PersonForm
  //end person form functions