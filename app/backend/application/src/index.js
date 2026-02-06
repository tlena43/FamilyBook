import React, { useState, useEffect, lazy, Suspense } from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  useLocation
} from "react-router-dom";
import {api} from "./global.js"
import { faBars} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

const LoginPage = lazy(() => import("./login"));
const PersonForm = lazy(() => import("./personform"))
const ContentForm = lazy(() => import("./contentform"))
const DisplayContent = lazy(() => import("./displaycontent"))
const DisplayPeople = lazy(() => import("./displaypeople"))
const IndividualPerson = lazy(() => import("./individualperson"))
const IndividualContent = lazy(() => import("./individualcontent"))





//start navigation functions
function NavItem({privacyLevel}){
  function navClick(){
    let nav = document.getElementById("nav-list-style")
    nav.className = ""
  }
  let items;
  if(privacyLevel !== "extended"){
    items = [{name: "Add Person", key: 1, route: "person/new"},
   {name: "People", key: 2, route: "person"},
  {name: "Add Content", key: 3, route: "content/new"},
  {name: "View Content", key: 4, route: "content"},
{name: "Log out", key: 5, route: "logout"}]
  }

  else{
    items = [
    {name: "People", key: 2, route: "person"},
   {name: "View Content", key: 4, route: "content"},
 {name: "Log out", key: 5, route: "logout"}]
  }


  let navItems = items.map((item) =>
<Link to={"/" + item.route}  className="nav-item" href="#top" id={item.name} key={item.key} onClick={navClick}>{item.name}</Link>
  );
  return(
    <div id="nav-list-style">
    <div id="nav-items">{navItems}</div>
    <div className="greyed-out"></div>

    </div>
  )}

function Header({privacyLevel}){
  function menuClick(){
    let nav = document.getElementById("nav-list-style")

    if(nav.className === ""){
      nav.className += "mobile-nav"
    }
    else{
      nav.className = ""
    }
  }
  return(
    <div id='head-wrapper'><div id='head'>
      <h1 id='header-title-container'>Kischook Family</h1>
      <FontAwesomeIcon icon={faBars} onClick={menuClick}/>
      <NavItem privacyLevel={privacyLevel} /></div></div>
    
  )
}
//end naviagtion functions

//start sitewide building
export default function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}

function LogOut(){
  localStorage.clear()
  window.location = "/login"
}

function PageState({setLoginKey, loginKey, privacyLevel, setPrivacyLevel}){
  if(loginKey == null){
    return(
      <Suspense fallback={<div>Loading...</div>}>
      <Routes>    
        <Route path="*" element={<LoginPage setLoginKey={setLoginKey} setPrivacyLevel={setPrivacyLevel}/>}/>
      </Routes>
      </Suspense>
    )
  }

  else if(privacyLevel === "extended"){
    console.log(privacyLevel)
    return(
      <div>
      <Header privacyLevel={privacyLevel}/>
      <div id='page-body'>
      <Suspense fallback={<div>Loading...</div>}>
      <Routes >
        <Route path="/person" element={<DisplayPeople loginKey={loginKey}/>}/>
        <Route path="/person/:id" element={<IndividualPerson loginKey={loginKey} admin={false}/>}/>
        <Route path="/content" element={<DisplayContent loginKey={loginKey}/>}/>
        <Route path="/" element={<DisplayContent loginKey={loginKey}/>}/>
        <Route path="/content/:id" element={<IndividualContent loginKey={loginKey} admin={false}/>}/>
        <Route path="/login" element={<LoginPage setLoginKey={setLoginKey}/>}/>
        <Route path="/logout" element={<LogOut/>}/>
        <Route path='*' element={<NotFound/>}/>
      </Routes>
      </Suspense>
      </div>
     </div>
    )
  }

  return(
    <div>
    <Header privacyLevel={privacyLevel} />
    <div id='page-body'>
    <Suspense fallback={<div>Loading...</div>}>
    <Routes >
      <Route exact path="/person/new" element={<PersonForm loginKey={loginKey}/>}/>
      <Route path="/person" element={<DisplayPeople loginKey={loginKey}/>}/>
      <Route path="/person/edit/:id" element={<PersonForm loginKey={loginKey}/>}/>
      <Route path="/person/:id" element={<IndividualPerson loginKey={loginKey} admin={true}/>}/>
      <Route path="/content/new" element={<ContentForm loginKey={loginKey}/>}/>
      <Route path="/content/edit/:id" element={<ContentForm loginKey={loginKey}/>}/>
      <Route path="/content" element={<DisplayContent loginKey={loginKey}/>}/>
      <Route path="/" element={<DisplayContent loginKey={loginKey}/>}/>
      <Route path="/content/:id" element={<IndividualContent loginKey={loginKey}  admin={true}/>}/>
      <Route path="/login" element={<LoginPage setLoginKey={setLoginKey}/>}/>
      <Route path="/logout" element={<LogOut/>}/>
      <Route path='*' element={<NotFound/>}/>
    </Routes>
    </Suspense>
    </div>
   </div>
  )

}


function NotFound(){
  return(
    <div>
      <h1>404</h1>
      <h1>The page you were looking for doesn't exist</h1>
    </div>
  )
}

function Main(){
  const [loginKey, setLoginKey] = useState(localStorage.getItem("key"))
  const [privacyLevel, setPrivacyLevel] = useState(localStorage.getItem("privacyLevel"))

  if(loginKey != null){
    fetch(api + "loginCheck",{
      method: "GET",
      headers:{
        "Content-Type" : "application/json",
        "X-api-key" : loginKey
      }
    })
    .then(response => {
      if(!response.ok){
        setLoginKey(null)
        setPrivacyLevel(null)
        localStorage.clear()
      }
    })
    
    
  }

  // checkStatus(loginKey, setLoginKey)

  return(
    <div id="main-page">
      <Router>
          <ScrollToTop/>
          <PageState setLoginKey={setLoginKey} loginKey={loginKey} privacyLevel={privacyLevel} setPrivacyLevel={setPrivacyLevel}/>
        </Router>
    </div>
  )
}


ReactDOM.render(
  <React.StrictMode>
    <Main/>
  </React.StrictMode>,
  document.getElementById('root')
);





