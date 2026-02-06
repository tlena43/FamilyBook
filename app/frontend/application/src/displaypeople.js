import React, { useState, useEffect } from 'react';
import './index.css';
import {fetchPeople} from "./formfunctions.js"
import Search from './search';

//person search
function ProcessPeopleAddContent({ personPromiseResolve, loginKey, promiseReject }) {
  const [errorPeople, setErrorPeople] = useState(null);
  const [loadingPeople, setLoadingPeople] = useState(true);
  async function getPeople() {
    try {
      setLoadingPeople(true);
      const valuePeople = await fetchPeople(loginKey);
      if(valuePeople){
        personPromiseResolve(valuePeople);
      }
      else{
        promiseReject();
      }


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
  return loadingPeople ? <div className="loader" >
  <div className='loader-bar' ></div></div>  : <div></div>
}

//start display people functions
const DisplayPeople = ({loginKey}) => {
    return(
      <div id="people-list">
        <ProcessPeople loginKey={loginKey}/>
      </div>
    )
  }
  
  
  function ProcessPeople({loginKey}){
    var personPromiseResolve, personPromiseReject;
    const personPromise = new Promise(function (resolve, reject) {
      personPromiseResolve = resolve;
      personPromiseReject = reject;
    });  
    return(  
      <div >
           <ProcessPeopleAddContent personPromiseResolve={personPromiseResolve} loginKey={loginKey} promiseReject={personPromiseReject}/>
            <Search details={personPromise} cardType="person"/>
            
      </div>
    )
  }

  export default DisplayPeople

