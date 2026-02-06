import React from 'react';
import './index.css';
import {useInput, LabelInputField} from "./formfunctions.js"
import {api} from "./global.js"



//start login content
const LoginPage = ({setLoginKey, setPrivacyLevel}) =>{
    const {value: username, bind: bindUsername, reset: resetUsername} = useInput("")
    const {value: password, bind: bindPassword, reset: resetPassword} = useInput("")
  
    const handleSubmit = (e) => {
        e.preventDefault()
        resetPassword()
        resetUsername()

        let content = {username: username, password: password}
        fetch(api + "login",{
            method: "POST",
            body: JSON.stringify(content),
            headers:{
              "Content-Type" : "application/json"
            }
          })
          .then(response => {
            if (!response.ok) {
              throw new Error('Response was not OK');
            }
            return response.json()})
          .then(data => {
            localStorage.setItem("key", data["key"])
            localStorage.setItem("privacyLevel", data["privacyLevel"])
            setLoginKey(data["key"])
            setPrivacyLevel(data["privacyLevel"])
            window.location = "/"
          })
          .catch(error => {
            console.log("Failed to fetch")
            alert("Failed to log in\nPlease review your login details and try again")
          })
          
          
    }

    return(
      <div id="login-page">
        <div className='form-style'>
          <h1>Welcome</h1>
          <h2 className='section'>Kischook Family History Database</h2>
          <div className='inner-wrap'>
          <p>This is a private collection of Kischook family history documents focused on the 
            children, grandchildren, and extended family of Alexandria Kischook. All members
            of the Kischook family are welcome to view and share documents. To request access, please
            contact our admin at Trent@Kischook.com. To submit a document, please email the document and
            all relevant information including names, dates, locations and any additional notes.
          </p>
          </div>
          <h2 className='section'>Login</h2>
          <form id="login-form" onSubmit={handleSubmit}>
            <div className='inner-wrap'>
              <LabelInputField binding={bindUsername} label={"Username"} id={"username-input"} type={"text"}/>
              <LabelInputField binding={bindPassword} label={"Password"} id={"password-input"} type={"password"}/>
            </div>
            <input type="submit" value="Submit"></input>
          </form>
        </div>
      </div>
    )
  }
  //end login content

//   ReactDOM.render(
//     <React.StrictMode>
//       <LoginPage/>
//     </React.StrictMode>,
//     document.getElementById('root')
//   );

export default LoginPage