import React from "react";
import "./index.css";
import { Link } from "react-router-dom";

/*
A card to display a preview of a person
*/


export default function PersonCard({ person, type }) {
  return (
    <Link to={"/person/" + person.getID()}>
      <div className={type}>
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