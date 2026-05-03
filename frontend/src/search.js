import React, { useMemo, useState } from "react";
import "./index.css";
import { Link } from "react-router-dom";
import { Person } from "./person.js";
import { api } from "./global.js";
import PersonCard from "./personcard.js";

// helpers needed for searches
function ContentCard({ content }) {
  return (
    <Link to={"/content/" + content.id}>
      <div className="content-card">
        <p>{content.title}</p>
        {checkIfCacheable(content.fileName) ? (
          <img
            alt="Content Preview"
            src={api + "upload/cache/" + getCacheFilename(content.fileName)}
          />
        ) : (
          <img alt="Content Preview" src={api + "upload/" + content.fileName} />
        )}
      </div>
    </Link>
  );
}

function getCacheFilename(filename) {
  const fileParts = filename.split(".");
  let cacheFilename = fileParts.slice(0, -1).join(".");
  cacheFilename += "_" + fileParts[fileParts.length - 1] + ".jpg";
  return cacheFilename;
}

function checkIfCacheable(filename) {
  const ext = filename.split(".").pop()?.toLowerCase();
  return ext === "pdf" || ext === "jpg" || ext === "jpeg" || ext === "png";
}

// start generic search
function SearchList({ filteredContent, cardType }) {
  if (!filteredContent || filteredContent.length === 0) {
    return (
      <div id={cardType + "-card-container"}>
        <div>
          <h3>No results found.</h3>
        </div>
      </div>
    );
  }

  const cards = filteredContent.map((i) => {
    if (cardType === "content") return <ContentCard content={i} key={i.id} />;
    if (cardType === "person")
      return <PersonCard key={i.id} person={new Person(i)} type={"content-card"} />;
    return null;
  });

  return <div id={cardType + "-card-container"}>{cards}</div>;
}

// actual search
export default function Search({ details = [], cardType, isLoading = false, error = null }) {
  const [searchField, setSearchField] = useState("");

  const filtered = useMemo(() => {
    const lowerSearchStr = searchField.toLowerCase();

    if (!Array.isArray(details)) return [];

    if (cardType === "content") {
      return details.filter((content) =>
        (content.title ?? "").toLowerCase().includes(lowerSearchStr)
      );
    }

    if (cardType === "person") {
      return details.filter((person) => {
        const fn = (person.firstName ?? "").toLowerCase();
        const mn = (person.middleName ?? "").toLowerCase();
        const ln = (person.lastName ?? "").toLowerCase();

        const personWithMiddle = [fn, mn, ln].filter(Boolean).join(" ");
        const personWithoutMiddle = [fn, ln].filter(Boolean).join(" ");

        return (
          personWithMiddle.includes(lowerSearchStr) ||
          personWithoutMiddle.includes(lowerSearchStr) ||
          fn.includes(lowerSearchStr) ||
          ln.includes(lowerSearchStr) ||
          mn.includes(lowerSearchStr)
        );
      });
    }

    return [];
  }, [details, cardType, searchField]);

  const handleChange = (e) => setSearchField(e.target.value);

  if (error) return "failed to load";
  if (isLoading) return "loading";

  return (
    <section>
      <div>
        <input
          type="search"
          placeholder="Type to Search"
          onChange={handleChange}
          className="search-bar"
        />
      </div>
      <SearchList filteredContent={filtered} cardType={cardType} />
    </section>
  );
}