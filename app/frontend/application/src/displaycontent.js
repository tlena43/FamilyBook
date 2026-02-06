import React, { useState, useEffect } from 'react';
import './index.css';
import {api} from "./global.js"
import Search from './search';


function ProcessDisplayContent({ promiseResolve, loginKey, promiseReject }) {
  const [errorContent, setErrorContent] = useState(null);
  const [loadingContent, setLoadingContent] = useState(true);
  async function getContent() {
    try {
      setLoadingContent(true);
      const valueContent = await fetchContentOverview(loginKey);
      if(valueContent){
        promiseResolve(valueContent);
      }
      else{
        promiseReject();
      }

    } catch (e) {
      setErrorContent(e);
    } finally {
      setLoadingContent(false);
    }
  }
  useEffect(() => {
    getContent();
  }, []);

  if (errorContent) return "Failed to load resource";
  return loadingContent ? <div className="loader" >
  <div className='loader-bar' ></div></div> : ""
}





function fetchContentOverview(loginKey){
  return new Promise(resolve => 
    fetch(api + "content",{
      method: "GET",
      headers:{
        "X-api-key" : loginKey
      }
    })
    .then(response => response.json())
    .then(data => {resolve(data["content"])
    }))
}

function ProcessContent({loginKey}){
  var contentPromiseResolve, contentPromiseReject;
  const contentPromise = new Promise(function (resolve, reject) {
    contentPromiseResolve = resolve;
    contentPromiseReject = reject;
  });


    return (
    <div>
      <ProcessDisplayContent promiseResolve={contentPromiseResolve} promiseReject = {contentPromiseReject} loginKey={loginKey} />
      <Search details={contentPromise} cardType="content"/>
    </div> )
}

//start display content functions
const DisplayContent = ({loginKey}) => {
    return(
      <div >
        <ProcessContent loginKey = {loginKey}/>
      </div>
    )
  }
  //end display content functions

  export default DisplayContent
