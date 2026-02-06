import React, { useState, useEffect } from 'react';
import './index.css';
import {fetchPerson} from "./formfunctions.js"
import {useParams, Link} from "react-router-dom";
import {Person} from "./person.js"
 
  
  const IndividualPerson = ({loginKey, admin}) => {
    let {id} = useParams();
    const [valuePerson, setValuePerson] = useState(null);
    const [errorPerson, setErrorPerson] = useState(null);
    const [loadingPerson, setLoadingPerson] = useState(true);
    async function getPerson() {
      try {
        setLoadingPerson(true);
        const person = await fetchPerson(id, loginKey)
        setValuePerson(person)
      } catch (e) {
        setErrorPerson(e);
      } finally {
        setLoadingPerson(false);
      }
    }
    useEffect(() => {
      getPerson();
    }, []);


  
    if (errorPerson) return "Failed to load resource";
      return loadingPerson ? <div className="loader" >
      <div className='loader-bar' ></div></div>  : 
      <div>
          <PersonDisplay person={ new Person(valuePerson)} content={valuePerson.content} admin={admin}/>
      </div>
  }

  function PersonDisplay({person, content, admin}){
    
      let deathDay = person.getDeathDay();

      let contentList = (content).map(item => (

        <Link to={"/content/" + item.id} key={item.id}>
        <p>{item.title}</p>
        </Link>
      ))

      return(
        <div className='form-style'>
            <h1 className='individual-name'> {person.getFullName()}</h1>
            <div className='inner-wrap'>
            <img className='individual-photo' alt='Profile' src={person.getFileName()}/>
            {person.getBirthday() === "" ? "" : <p>Birth Date: {person.getBirthday()}</p>}
            {person.getBirthPlace() ? <p>Birth Place: {person.getBirthPlace()}</p> : <p></p>}
            {person.getMaidenName() ? <p>Maiden Name: {person.getMaidenName()}</p> : <p></p>}
            {deathDay ? <p>Death Date: {deathDay}</p> : <p></p>}
            {content.length ? <p>Tagged Content:</p> : <p></p>}
            {contentList}
            {admin ?  <Link to={"/person/edit/" + person.getID()}><button>Edit</button></Link> : <p></p>}
           
            </div>
        </div>
      )
  }

  export default IndividualPerson