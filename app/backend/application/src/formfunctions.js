import React, { useState, useEffect } from 'react';
import './index.css';
import { api } from "./global.js"

const monthList = ["Unknown", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];
const dayList = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

//start form functions
function ValidateFebruary(year, day) {
  if (day === 29) {
    if (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)) {
      return (true)
    }
    return (false)
  }
  return (true)
}

export const validateDates = (month, day, year) => {
  var isFebValid = ValidateFebruary(year, day)
  if (!isFebValid) {
    return ([false, "You selected February 29th without a leap year!"])
  }

  var today = new Date()
  var inputDateInfo = processDate(month, day, year)


  if (inputDateInfo[1] <= today) {
    return (inputDateInfo)
  }

  return ([false, "Your date can't be in the future!"])
}

export const useInput = initialValue => {
  const [value, setValue] = useState(initialValue);

  return {
    value,
    setValue,
    reset: () => setValue(""),
    bind: {
      value,
      onChange: event => {
        setValue(event.target.value);
      }
    }
  };
};

export const useMonth = initialValue => {
  const [value, setValue] = useState(initialValue);
  const [numDays, setNumDays] = useState(0)

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
      onChange: e => {
        let curMonth = e.target.value;
        setValue(curMonth);
        if (curMonth !== "Unknown") {

          let monthIndex = monthList.indexOf(curMonth) - 1;

          setNumDays(dayList[monthIndex])
        }
        else {
          setNumDays(0)
        }
      }
    }
  };
};

export const CheckBox = initialValue => {
  const [value, setValue] = useState(initialValue);
  const [checked, setChecked] = useState(false)

  return {
    value,
    setValue,
    checked,
    setChecked,
    reset: () => {
      setValue("")
      setChecked(false)
    },
    bind: {
      value,
      onChange: event => {
        setValue(event.target.value);
        if (checked === true) {
          setChecked(false)
        }
        else {
          setChecked(true)
        }
      }
    }
  };
}

function processDate(month, day, year) {
  var unknowns = 0;
  var date;

  if (year === "") {
    unknowns = 3;
    date = null
  }
  else if (month === "Unknown" || month === "") {
    unknowns = 2;
    date = new Date(year, 0, 1)
  }
  else if (day === "Unknown" | day === "") {
    unknowns = 1;
    date = new Date(year, monthList.indexOf(month) - 1, 1)
  }
  else {
    date = new Date(year, monthList.indexOf(month) - 1, day)
  }

  return ([unknowns, date])
}

export const unpackDate = (date, unknowns) => {
  let stringDate = ""

  var monthIndex = date.getUTCMonth()


    if (unknowns === 0) {
      stringDate = monthList[monthIndex + 1] + " " + date.getUTCDate(date) + " " + date.getUTCFullYear()

    }
    else if (unknowns === 1) {
      stringDate = monthList[monthIndex + 1] + " " + date.getUTCFullYear()
    }
    else if (unknowns === 2) {
      stringDate = date.getUTCFullYear()

    }
    else {
      stringDate = "Date Unknown"
    }

    return (stringDate)
  }


function fetchGender() {
  return new Promise(resolve => {
    fetch(api + "gender", {
      method: "GET",

    })
      .then(response => response.json())
      .then(data => {
        resolve(data["genders"])
      })
  })
}

export const ProcessGender = ({ setGender }) => {
  const [valueGender, setValueGender] = useState(null);
  const [errorGender, setErrorGender] = useState(null);
  const [loadingGender, setLoadingGender] = useState(true);
  async function getGender() {
    try {
      setLoadingGender(true);
      const valueGender = await fetchGender();
      setValueGender(valueGender);
    } catch (e) {
      setErrorGender(e);
    } finally {
      setLoadingGender(false);
    }
  }
  useEffect(() => {
    getGender();
  }, []);

  var handleRadioChange = (e) => {
    setGender(e.target.value)
  }

  if (errorGender) return "Failed to load resource A";
  return loadingGender ? "Loading..." :
    <div>
      <label id="gender-label">Gender:</label>
      <div className="radio-group">

        {(valueGender).map(i => (
          <LabelInputField name={"gender"} key={i["name"]} onChange={handleRadioChange} label={i["name"]} type={"radio"} id={i["name"]} value={i["id"]} />
        ))}
      </div></div>;
}

export const DateBundle = ({ label, binding, id, num, show }) => {
  if (show === false) {
    return (
      <div></div>
    )
  }
  return (
    <div className="date-bundle">
      {/* <p>{label}</p> */}
      <LabelInputField binding={binding[0]} label={"Year"} type={"text"} id={id[0]} />
      <SelectField binding={binding[1]} id={id[1]} array={monthList} label={"Month"} />
      <DayField num={num} id={id[2]} binding={binding[2]}></DayField>
    </div>
  )
}

export const separateDate = (date, unknowns) => {
  var dateObj = new Date(date)
  var monthListIndex = monthList[dateObj.getUTCMonth() + 1]
  var dayListIndex = dayList[dateObj.getUTCMonth()]
  var day = dateObj.getUTCDate()
  var year = dateObj.getUTCFullYear();


  if (unknowns >= 1) {
    dayListIndex = 0
    if (unknowns >= 2) {
      monthListIndex = 0
      if (unknowns === 3) {
        year = ""
      }
    }
  }

  return ({ month: monthListIndex, day: day, year: year, daysNum: dayListIndex })
}

function DayField({ num, binding }) {
  if (num > 0) {
    return (
      <div className="day-field"> <label for="day">Day</label>
        <select id="day" name="day" {...binding} className="box-input">
          <option value="" selected disabled hidden >Select</option>
          <option value="Unknown">Unknown</option>
          {
            (Array.apply(null, Array(num)).map(function (x, i) { return i; })).map((item, index) => (
              <option key={index} value={index + 1}>{index + 1}</option>
            ))}
        </select> </div>
    )
  }

  return (
    <div></div>
  )
}

export const LabelInputField = ({ binding, label, type, id, name, value, onChange }) => {
  if (type === "checkbox") {
    return (
      <div className="label-input-field">
        <label for={id} className="checkbox-label">
          {label}
          <input type={type} name={name} {...binding} id={id} value={value}></input>
        </label>
      </div>
    )
  }
  if (type === "radio") {
    return (
      <div className="label-input-field ">
        <label for={id}>
          <input type={type} name={name} {...binding} id={id} value={value} onChange={onChange} className="radio-box"></input>
          {label}
        </label>
      </div>
    )
  }

  if (type === "textarea") {
    return (
      <div className="label-input-field">
        <label for={id}>
          {label}
          <textarea {...binding} id={id} className="box-input"></textarea>
        </label>
      </div>
    )
  }
  return (
    <div className="label-input-field">
      <label for={id}>
        {label}
        <input type={type} {...binding} id={id} className="box-input"></input>
      </label>
    </div>
  )
}

export const SelectField = ({ binding, array, id, label }) => {
  return (
    <div className="select-container">
      <label for={id}>{label}
        <select id={id} name={id} {...binding} className="box-input ">
          <option value="" selected disabled hidden >Select</option>
          {array.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </label>
    </div>
  )
}

export const fetchPeople = (loginKey) => {
  return new Promise(resolve => {
    fetch(api + "person", {
      method: "GET",
      headers: {
        "X-api-key": loginKey
      }
    })
      .then(response => response.json())
      .then(data => {
        resolve(data["people"])
      })
  })
}

export const fetchPerson = (id, loginKey) => {
  return new Promise(resolve => {
    fetch(api + "person/" + id, {
      method: "GET",
      headers: {
        "X-api-key": loginKey
      }
    })
      .then(response => response.json())
      .then(data => {
        resolve(data)
      })
  })
}

export const fetchContent = (id, loginKey) => {
  return new Promise(resolve => {
    fetch(api + "content/" + id, {
      method: "GET",
      headers: {
        "X-api-key": loginKey
      }
    })
      .then(response => response.json())
      .then(data => {
        resolve(data)
      })
  })
}
  //end form functions
