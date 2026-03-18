import React from "react";
import "./index.css";
import { Link } from "react-router-dom";


export default function PersonCard({ person }) {
  return (
    <Link to={"/person/" + person.getID()}>
      <div className="content-card">
        <p>
          {person.getFullName()}
          <br />
          {person.getBirthday()}
        </p>
        <img alt="Profile" src={person.getCachedFileName()} />
      </div>
    </Link>
  );
}