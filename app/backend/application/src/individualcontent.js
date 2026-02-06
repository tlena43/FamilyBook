import React, { useState, useEffect } from 'react';
import './index.css';
import {unpackDate, fetchContent} 
from "./formfunctions.js"
import {useParams, Link} from "react-router-dom";
import {api} from "./global.js"


  
  const IndividualContent = ({loginKey, admin}) => {
    let {id} = useParams();
    const [valueContent, setValueContent] = useState(null);
    const [errorContent, setErrorContent] = useState(null);
    const [loadingContent, setLoadingContent] = useState(true);
    async function getContent() {
      try {
        setLoadingContent(true);
        const content = await fetchContent(id, loginKey)
        setValueContent(content)
      } catch (e) {
        setErrorContent(e);
      } finally {
        setLoadingContent(false);
      }
    }
    useEffect(() => {
      getContent();
    }, []);

  
    if (errorContent) return "Failed to load resource A";
      return loadingContent ? <div className="loader" >
      <div className='loader-bar' ></div></div> : 
      <div>
          <ContentDisplay content={valueContent} id={id} admin={admin}/>
      </div>
  }

  function ContentDisplay({content, id, admin}){
      let date = unpackDate(new Date(content.date), content.dateUnknowns)
      let people = (content.people).map(person => (

        <Link to={"/person/" + person.id} key={person.id}>
        <p>{person.firstName} {person.middleName} {person.lastName}</p>
        </Link>
      ))
      return(
        <div className='individual-content-page form-style'>
            <h1>
                {content.title}
            </h1>
            <div className='inner-wrap'>
            {content.fileName.split(".")[1] === "pdf" ?
         <div className='pdf-preview'>
         <PDFViewer fileName={content.fileName}/>
       </div>      :
        <img alt='Content' src={api + "upload/" + content.fileName}/>}   
            <a href={api + "upload/" + content.fileName} download><p>Download</p></a>
            <p>Date: {date}</p>
            {content.people.length ? <p>People Involved:</p> : <p></p>}
            {people}
            {content.type ? <p>Content Type: {content.type}</p> : <p></p>}
            {content.notes ? <p>Notes: {content.notes}</p> : <p></p>}
            {content.location ? <p>Location: {content.location}</p> : <p></p>}
            {admin ? <Link to={"/content/edit/" + id}><button>Edit</button></Link> : <p></p>}
            
            </div>
        </div>
      )
  }

  function StackedImage({ src, loaded, setLoaded }){
    return (
      <div>{loaded ? null : <div>Loading...</div>}
        <img style={loaded ? {} : { display: 'none' }}
          src={src} onLoad={() => setLoaded(true)} alt="Content"/>
      </div>
    );
  };


  function PDFViewer({fileName}) {
 
    const [numPages, setNumPages] = useState();
    const [pageNumber, setPageNumber] = useState(1);
    // let pages;
    const [loaded, setLoaded] = useState(false);
  const [errorNumPages, setErrorNumPages] = useState(null);
  const [loadingNumPages, setLoadingNumPages] = useState(true);

  function fetchNumPages(fileName){
        return new Promise(resolve => {
    fetch(api + "upload/num_pages/" + fileName,{
      method: "GET",
    })
    .then(response => response.json())
    .then(data => {
      resolve(data)
    })
  })
  }


  async function getNumPages() {
    try {
      setLoadingNumPages(true);
      const numPages = await fetchNumPages(fileName);
      setNumPages(numPages['num_pages']);

    } catch (e) {
      setErrorNumPages(e);
    } finally {
      setLoadingNumPages(false);
    }
  }
  useEffect(() => {
    getNumPages();
  }, []);


      function getCacheFilename(filename, pageNum) {
    var fileParts = filename.split('.')
    var cacheFilename = fileParts.slice(0, -1).join('.')
    cacheFilename += '_' + fileParts[fileParts.length - 1] + "_" + pageNum + '.jpg'
    return cacheFilename
  }
  
    function changePage(offset) {
      setPageNumber(prevPageNumber => prevPageNumber + offset);
      setLoaded(false)
    }
  
    function previousPage() {
      changePage(-1);
    }
  
    function nextPage() {
      changePage(1);
    }


  
    return (
      <>
        <StackedImage  src={api + "upload/cache/" + getCacheFilename(fileName, pageNumber)} loaded={loaded} setLoaded={setLoaded} />
        <div className='pagination-display'>
        <button type="button" disabled={pageNumber <= 1}
            onClick={previousPage} className="pdf-nav">Previous</button>
          <p>
            Page {pageNumber || (numPages ? 1 : '--')} of {numPages || '--'}
          </p>
          <button type="button" disabled={pageNumber >= numPages}
            onClick={nextPage} className="pdf-nav">
            Next
          </button>
        </div>
      </>
    );
  }
  export default IndividualContent
