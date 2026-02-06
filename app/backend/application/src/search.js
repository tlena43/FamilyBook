import React, { useState, useEffect } from 'react';
import './index.css';
import { Link } from 'react-router-dom';
import { Person } from "./person.js"
import { api } from "./global.js"

//helpers needed for searches
function PersonDisplay({ person }) {
    return (
        <Link to={"/person/" + person.getID()} >
            <div className='content-card'>
                <p>{person.getFullName()}
                    <br />{person.getBirthday()}</p>
                <img alt="Profile" src={person.getCachedFileName()} />
            </div>
        </Link>
    );
}

function ContentCard({ content }) {
    return (
        <Link to={"/content/" + content.id} >
            <div className='content-card'>
                <p>{content.title}</p>
                {checkIfCacheable(content.fileName) ?
                    <img alt="Content Preview" src={api + "upload/cache/" + getCacheFilename(content.fileName)} /> :
                    <img alt='Content Preview' src={api + "upload/" + content.fileName} />}
            </div>
        </Link>
    )
}

function getCacheFilename(filename) {
    var fileParts = filename.split('.')
    var cacheFilename = fileParts.slice(0, -1).join('.')
    cacheFilename += '_' + fileParts[fileParts.length - 1] + '.jpg'
    return cacheFilename
}

function checkIfCacheable(filename) {
    let ext = filename.split(".")[1]
    if (ext === 'pdf' || ext === 'jpg' || ext === 'jpeg' || ext === 'png') {
        return true
    }
    return false
}


//start generic search
//
//
//
//
function SearchList({ filteredContent, cardType }) {
    let filtered
    if (filteredContent.length !== 0) {
        filtered = filteredContent.map(i => {
            if (cardType === "content") {
                return <ContentCard content={i} key={i.id} />
            }
            else if (cardType === "person") {
                return <PersonDisplay key={i.id} person={new Person(i)} />
            }
        });
    }
    else {
        filtered =
            <div>
                <h3>Hmm We can't seem to find anything here</h3>
            </div>
    }
    return (
        <div id={cardType + "-card-container"}>
            {filtered}
        </div>
    );
}

//actual search
export default function Search({ details, cardType }) {
    const [valueSearch, setValueSearch] = useState([]);
    const [errorSearch, setErrorSearch] = useState(null);
    const [loadingSearch, setLoadingSearch] = useState(true);
    const [searchField, setSearchField] = useState("");


    async function searchReady() {
        try {
            setLoadingSearch(true);
            await details.then((v) => {
                setValueSearch(v)

            });
        } catch (e) {
            setErrorSearch(e);
        } finally {
            setLoadingSearch(false);
        }
    }
    useEffect(() => {
        searchReady();
    }, []);
    var filtered;
    if (cardType === "content") {
        filtered = valueSearch.filter(
            content => {
                let lowerTitle = content.title.toLowerCase()
                let lowerSearchStr = searchField.toLowerCase();
                return (
                    lowerTitle.includes(lowerSearchStr)
                )
            }
        )
    }
    else if (cardType === "person") {
        filtered = valueSearch.filter(
            person => {
                let lowerFnStr = person.firstName.toLowerCase()
                let lowerLnStr = person.lastName.toLowerCase()
                var lowerMnStr = ""
                var personStr = lowerFnStr + " "
                var personWithoutMiddleStr = personStr + lowerLnStr
                if (person.middleName != null) {
                    lowerMnStr = person.middleName.toLowerCase()
                    personStr += lowerMnStr + " "
                }
                personStr += lowerLnStr
                let lowerSearchStr = searchField.toLowerCase();

                return (
                    personStr.includes(lowerSearchStr) ||
                    personWithoutMiddleStr.includes(lowerSearchStr) ||
                    lowerFnStr.includes(lowerSearchStr) ||
                    lowerLnStr.includes(lowerSearchStr) ||
                    lowerMnStr.includes(lowerSearchStr)
                )
            }
        )
    }



    const handleChange = e => {
        setSearchField(e.target.value);
    };
    if(errorSearch) return("failed to load")
    return loadingSearch ? "loading" :
    (
        <section>
            <div>
                <input
                    type="search" placeholder="Type to Search"
                    onChange={handleChange} className="search-bar"
                />
            </div>
            <SearchList filteredContent={filtered} cardType={cardType} />
        </section>
    );

}
