import React, { useState, useEffect } from 'react';
import './index.css';
function ContentCard  ({content})  {
    return(
      <div className='content-card'>
          <p>{content.title}</p>
        <img src={api + "upload/" + content.fileName}/>
      </div>
    )
  }