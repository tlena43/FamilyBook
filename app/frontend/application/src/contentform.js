import React, { useState, useEffect } from 'react';
import './index.css';
import { useInput, fetchContent, LabelInputField, useMonth, SelectField, validateDates,
  DateBundle, fetchPeople, separateDate} from "./formfunctions.js"
import { api } from "./global.js"
import { Person } from "./person.js"
import { useParams } from "react-router-dom";



function ProcessPeopleAddContent({ personPromiseResolve, loginKey }) {
  const [valuePeople, setValuePeople] = useState(null);
  const [errorPeople, setErrorPeople] = useState(null);
  const [loadingPeople, setLoadingPeople] = useState(true);
  async function getPeople() {
    try {
      setLoadingPeople(true);
      const valuePeople = await fetchPeople(loginKey);
      setValuePeople(valuePeople);
      personPromiseResolve(valuePeople);

    } catch (e) {
      setErrorPeople(e);
    } finally {
      setLoadingPeople(false);
    }
  }
  useEffect(() => {
    getPeople();
  }, []);

  if (errorPeople) return "Failed to load resource A";
  return loadingPeople ? "Loading..." : ""
}

function PersonDisplay({ person, selectedList, setSelectedList }) {
  const [className, setClassName] = useState("not-selected search-option")
  function personDisplayClick() {
    if (selectedList.some(personArr => personArr.id === person.id)) {
      setSelectedList(selectedList.filter(item => item.id !== person.id))
    }
    else {
      setSelectedList(arr => [...arr, person])
    }
  }

  useEffect(() => {
    if (selectedList.some(personArr => personArr.id === person.id)) {
      setClassName("is-selected search-option")
    }
    else {
      setClassName("not-selected search-option")
    }
  })

  return (
    <div>
      <div onClick={personDisplayClick} className={className}>
        <p className='search-name-text'>{person.getFullName()}</p>
        <p className='subtext'>Born: {person.getBirthday()}</p>
      </div>
    </div>

  );
}


//start search f-ns
//search list
function SearchList({ filteredPersons, selectedList, setSelectedList }) {
  const filtered = filteredPersons.map(person =>
    <PersonDisplay key={person.id} person={new Person(person)} selectedList={selectedList} setSelectedList={setSelectedList} />);
  return (
    <div >
      {filtered}
    </div>
  );
}

//overflow scroll
const Scroll = (props) => {
  return (
    <div className='search-scroll'>
      {props.children}
    </div>
  );
}

//actual search
function Search({ details, selectedList, setSelectedList }) {
  const [valueSearch, setValueSearch] = useState([]);
  const [errorSearch, setErrorSearch] = useState(null);
  const [loadingSearch, setLoadingSearch] = useState(true);
  const [searchField, setSearchField] = useState("");

  async function searchReady() {
    try {
      setLoadingSearch(true);
      await details.then((v) => {
        setValueSearch(v)

      });
    } catch (e) {
      setErrorSearch(e);
    } finally {
      setLoadingSearch(false);
    }
  }
  useEffect(() => {
    searchReady();
  }, []);

  var filtered = valueSearch.filter(
    person => {
      let lowerFnStr = person.firstName.toLowerCase()
      let lowerLnStr = person.lastName.toLowerCase()
      var lowerMnStr = ""
      var personStr = lowerFnStr + " "
      var personWithoutMiddleStr = personStr + lowerLnStr
      if (person.middleName != null) {
        lowerMnStr = person.middleName.toLowerCase()
        personStr += lowerMnStr + " "
      }
      personStr += lowerLnStr
      let lowerSearchStr = searchField.toLowerCase();

      return (
        personStr.includes(lowerSearchStr) ||
        personWithoutMiddleStr.includes(lowerSearchStr) ||
        lowerFnStr.includes(lowerSearchStr) ||
        lowerLnStr.includes(lowerSearchStr) ||
        lowerMnStr.includes(lowerSearchStr)
      )
    }
  )


  const handleChange = e => {
    setSearchField(e.target.value);
  };

  function removeBtnClick(index) {
    setSelectedList(selectedList.filter(item => item !== selectedList[index]))
  }

  const selectedPeople = selectedList.map((person, index) =>
    <li key={person.id}>
      <button className='remove-selected-btn' onClick={() => removeBtnClick(index)} type="button"> &#10006;</button>

      <p className='search-name-text'>{person.getFullName()}</p>
      <p className='subtext'>Born: {person.getBirthday()}</p></li>
  );

  return (
    <section>
      <div>
        <input
          type="search" placeholder="Type to Search"
          onChange={handleChange} className="box-input"
        />
      </div>
      <Scroll>
        <SearchList filteredPersons={filtered} selectedList={selectedList} setSelectedList={setSelectedList} />
      </Scroll>
      <label id='selected-label' for="selected-list">Selected People</label>
      <ul id="selected-list">{selectedPeople}</ul>

    </section>
  );

}
//end search f-ns

//start add content functions
const ContentForm = ({ loginKey }) => {
  const [valueContent, setValueContent] = useState(null);
  const [errorContent, setErrorContent] = useState(null);
  const [loadingContent, setLoadingContent] = useState(true);
  const { value: fileTitle, bind: bindFileTitle, reset: resetFileTitle, setValue: setFileTitle } = useInput("")
  const { value: notes, bind: bindNotes, reset: resetNotes, setValue: setNotes } = useInput("")
  const { value: location, bind: bindLocation, reset: resetLocation, setValue: setLocation } = useInput("")
  const { value: month, numDays: numDays, bind: bindMonth, reset: resetMonth, setValue: setMonth, setNumDays: setNumDays } = useMonth('')
  const { value: day, bind: bindDay, reset: resetDay, setValue: setDay } = useInput('')
  const { value: year, bind: bindYear, reset: resetYear, setValue: setYear } = useInput('')
  const [selectedList, setSelectedList] = useState([]);
  const { value: privacy, bind: bindPrivacy, reset: resetPrivacy, setValue: setPrivacy } = useInput("")
  const { value: contentType, bind: bindContentType, reset: resetContentType, setValue: setContentType } = useInput();
  let privacyOpts = ["Admin Only", "Close Family", "Extended Family"]
  let contentOpts = ["Newspaper", "Obituary", "Certificate", "Photo", "Legal Documents", "Other"]
  let { id } = useParams();
  const [editing, setEditing] = useState(id)
  var personPromiseResolve, personPromiseReject;
  const personPromise = new Promise(function (resolve, reject) {
    personPromiseResolve = resolve;
    personPromiseReject = reject;
  });
  const [storedFile, setStoredFile] = useState("")
  const [isUploading, setIsUploading] = useState("")


  async function getContent() {
    if (id !== undefined) {
      try {
        setLoadingContent(true);
        const contentEdit = await fetchContent(id, loginKey)
        setValueContent(contentEdit)
        setFileTitle(contentEdit.title)
        setNotes(contentEdit.notes ? contentEdit.notes : "")
        setLocation(contentEdit.location ? contentEdit.location : "")
        let contentDate = separateDate(contentEdit.date, contentEdit.dateUnknowns)
        setMonth(contentDate.month ? contentDate.month : "")
        setDay(contentDate.day ? contentDate.day : "")
        setYear(contentDate.year ? contentDate.year : "")
        setNumDays(contentDate.daysNum)
        setPrivacy(privacyOpts[contentEdit.privacy - 1])
        setContentType(contentEdit.type)
        setStoredFile(contentEdit.fileName)
        let peopleArr = contentEdit.people
        console.log(peopleArr)
        let mapRes = peopleArr.map(person => (
          new Person(person)
        ))
        console.log(mapRes)
        setSelectedList(mapRes)

      } catch (e) {
        setErrorContent(e);
      } finally {
        setLoadingContent(false);
      }

    }
  }
  useEffect(() => {
    getContent();
  }, []);

  function resetStates() {
    resetFileTitle();
    resetNotes();
    resetLocation();
    resetMonth();
    resetDay();
    resetYear();
    resetPrivacy();
    resetContentType();
    setSelectedList([]);
  }

  const handleSubmit = (e) => {
    e.preventDefault();
    let alertStr = "";
    let contentDateFull = validateDates(month, day, year);

    if (fileTitle.length > 50) {
      alertStr += "Title can not exceed 50 characters\n"
    }
    if (fileTitle === "") {
      alertStr += "Title can not be blank\n"
    }
    if (contentDateFull[0] === false) {
      alertStr += ("Your date is invalid. " + contentDateFull[1] + "\n")
    }
    if (privacyOpts.indexOf(privacy) === -1) {
      console.log(privacy)
      alertStr += "A privacy level must be selected\n"
    }
    if (!editing) {
      if (document.getElementById("content-file").files.length === 0) {
        alertStr += "A file must be uploaded\n"
      }
    }
    if (alertStr !== "") {
      alert(alertStr)
      return ("")
    }


    let selectedListID = []
    selectedList.map(person => selectedListID.push(person.id))
    let content = {
      user: 1, privacy: (privacyOpts.indexOf(privacy) + 1), type: (contentOpts.indexOf(contentType) + 1),
      date: contentDateFull[1], notes: notes.trim(), title: fileTitle.trim(),
      people: selectedListID, location: location.trim(), dateUnknowns: contentDateFull[0]
    }




    resetStates();

    if (!editing) {
      const fileField = document.getElementById("content-file")
      const formData = new FormData();
      formData.append("upload", fileField.files[0])
      fileField.value = null;
      setIsUploading("loader")
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
          content["file"] = data["fileid"]
          fetch(api + "content", {
            method: "POST",
            body: JSON.stringify(content),

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
              window.location = ("/content/" + data["id"])
            })

            .catch(error => {
              console.error('There has been a problem with your fetch operation:', error);
            })
        })
        .catch(error => {
          console.error('There has been a problem with your fetch operation:', error);
        })
    }
    else {
      contentPatch(loginKey, id, content)
    }

  }


  return (
    <div className={isUploading} >
      <div className='loader-bar' ></div>
      <div className="form-style">
        <h1>Add a Document</h1>
        <form onSubmit={handleSubmit} id="content-form">
          <div className='section'><span>1</span>Upload a file</div>
          <div className='inner-wrap'>
            {editing ? <p>Can not edit files</p> :
              <input type="file" id="content-file" name="filename" />}
            <LabelInputField binding={bindFileTitle} label={"Add a Title"} id={"file-title"} />
            <SelectField binding={bindPrivacy} id={"privacy-select"} label={"Privacy Level"} array={privacyOpts} />
          </div>
          <div className="section"><span>2</span>Who is this document about?</div>
          <div className="inner-wrap">
            {/* <LabelInputField binding={bindAddPerson} label={"Type name to select"} type={"text"} id={"add-person-content"} /> */}
            {/* <DisplayPeopleAddContent personPromiseResolve={personPromiseResolve}/> */}
            <div>
              <ProcessPeopleAddContent personPromiseResolve={personPromiseResolve} loginKey={loginKey} />
              <Search details={personPromise} selectedList={selectedList} setSelectedList={setSelectedList} />
            </div>
          </div>
          <div className='section'><span>3</span>Optional details</div>
          <div className='inner-wrap'>
            <SelectField binding={bindContentType} id={"content-type-select"} label={"Content Type"} array={contentOpts} />
            <LabelInputField binding={bindNotes} label={"Notes"} id={"content-notes"} type={"textarea"} />
            <LabelInputField binding={bindLocation} label={"Location"} id={"content-location"} type={"text"} />
            <DateBundle label={"Date"} binding={[bindYear, bindMonth, bindDay]}
              id={["content-year", "content-month", "content-day"]} num={numDays} show={true} />
          </div>
          <input type="submit" value="Submit" />
          {editing ? <button type="button" className='delete-btn' onClick={() => contentDelete(loginKey, id, storedFile)}>Delete</button> : <></>}
        </form>
      </div>
    </div>
  )
}
//end add content functions

function contentPatch(loginKey, id, content) {
  fetch(api + "content/" + id, {
    method: "PATCH",
    body: JSON.stringify(content),
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
      window.location = ("/content/" + data["id"])
    })
    .catch(error => {
      console.error('There has been a problem with your fetch operation:', error);
    })
}

function contentDelete(loginKey, id, file) {
  fetch(api + "content/" + id, {
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
          window.location = ("/content")
        })
        .catch(error => {
          console.error('There has been a problem with your fetch operation:', error);
        })
    })
    .catch(error => {
      console.error('There has been a problem with your fetch operation:', error);
    })
}

export default ContentForm